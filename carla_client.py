#!/usr/bin/env python3
"""
CARLA SOME/IP Client — ponto de entrada da simulacao.

Conecta ao CARLA, coleta telemetria via sensores + ground truth ADAS
e publica na rede SOME/IP via bridge TCP para o container ecu_bridge.

Uso:
    python carla_client.py --sync --autopilot --map Town10HD_Opt --duration 180
"""

from __future__ import print_function

import argparse
import logging
import math
import random
import sys
import time

import numpy as np
import carla
import pygame

sys.path.append('F:/Mestrado/CARLA/WindowsNoEditor/PythonAPI/carla')

from hud import HUD, ACAO_SAIR, ACAO_REINICIAR, ACAO_MAIS_VEL, ACAO_MENOS_VEL
from scripts import bridge_sender

RAIO_ADAS = 50.0   # metros — raio de deteccao ground truth


# ── Mundo / sensores ─────────────────────────────────────────────────────────

def _configurar_mundo(client, mapa, frequencia):
    world = None
    for tentativa in range(15):
        try:
            world      = client.get_world()
            mapa_atual = world.get_map().name
            break
        except Exception:
            logging.info('Aguardando mapa... (%d/15)', tentativa + 1)
            time.sleep(4.0)

    if world is None:
        raise RuntimeError('CARLA nao respondeu. Verifique se o simulador esta aberto.')

    if mapa not in world.get_map().name:
        logging.info('Carregando mapa %s (aguarde ~60s)...', mapa)
        client.set_timeout(120.0)
        world = client.load_world(mapa)
        client.set_timeout(60.0)
        time.sleep(5.0)

    settings = world.get_settings()
    settings.synchronous_mode    = True
    settings.fixed_delta_seconds = 1.0 / frequencia
    world.apply_settings(settings)
    world.set_weather(carla.WeatherParameters.ClearNoon)
    return world


def _criar_traffic_manager(client):
    tm = client.get_trafficmanager()
    tm.set_global_distance_to_leading_vehicle(2.0)
    tm.set_synchronous_mode(True)
    return tm


def _spawnar_ego(world, tm, rolename='ego'):
    lib    = world.get_blueprint_library()
    pontos = world.get_map().get_spawn_points()
    bp = lib.find('vehicle.tesla.model3')
    bp.set_attribute('role_name', rolename)
    bp.set_attribute('color', '255,0,0')
    v = world.spawn_actor(bp, pontos[0])
    v.set_autopilot(True, tm.get_port())
    return v


def _spawnar_npcs(world, tm, num_npcs):
    lib    = world.get_blueprint_library()
    pontos = world.get_map().get_spawn_points()
    bps    = [b for b in lib.filter('vehicle.*')
              if int(b.get_attribute('number_of_wheels')) == 4]
    npcs   = []
    for ponto in pontos[1: num_npcs + 1]:
        bp = random.choice(bps)
        if bp.has_attribute('color'):
            bp.set_attribute('color', random.choice(bp.get_attribute('color').recommended_values))
        try:
            npc = world.try_spawn_actor(bp, ponto)
            if npc:
                npc.set_autopilot(True, tm.get_port())
                npcs.append(npc)
        except Exception:
            pass
    logging.info('%d NPCs spawnados', len(npcs))
    return npcs


def _adicionar_sensores(world, veiculo, frequencia):
    lib      = world.get_blueprint_library()
    sensores = {}

    bp_gnss = lib.find('sensor.other.gnss')
    bp_gnss.set_attribute('sensor_tick', str(1.0 / frequencia))
    gnss = world.spawn_actor(bp_gnss, carla.Transform(), attach_to=veiculo)
    sensores['gnss'] = {'ator': gnss, 'dado': None}
    gnss.listen(lambda d: sensores['gnss'].update({'dado': d}))

    bp_imu = lib.find('sensor.other.imu')
    bp_imu.set_attribute('sensor_tick', str(1.0 / frequencia))
    imu = world.spawn_actor(bp_imu, carla.Transform(), attach_to=veiculo)
    sensores['imu'] = {'ator': imu, 'dado': None}
    imu.listen(lambda d: sensores['imu'].update({'dado': d}))

    bp_lidar = lib.find('sensor.lidar.ray_cast')
    bp_lidar.set_attribute('channels',          '32')
    bp_lidar.set_attribute('points_per_second', '56000')
    bp_lidar.set_attribute('range',             '50')
    bp_lidar.set_attribute('sensor_tick',       str(1.0 / frequencia))
    lidar = world.spawn_actor(bp_lidar,
                              carla.Transform(carla.Location(x=0, z=2.5)),
                              attach_to=veiculo)
    sensores['lidar'] = {'ator': lidar, 'dado': None, 'pts_xy': None}

    def _on_lidar(data):
        pts = np.frombuffer(data.raw_data, dtype=np.float32).copy().reshape((-1, 4))
        step = max(1, len(pts) // 2000)
        sensores['lidar']['dado']   = data
        sensores['lidar']['pts_xy'] = pts[::step, :2].tolist()

    lidar.listen(_on_lidar)

    return sensores


def _adas_ground_truth(world, veiculo):
    ego_t   = veiculo.get_transform()
    ego_loc = ego_t.location
    fwd     = ego_t.get_forward_vector()

    veiculos, pedestres, semaforos = [], [], []
    lidar_objects = []

    for a in world.get_actors().filter('vehicle.*'):
        if a.id == veiculo.id:
            continue
        loc = a.get_location()
        dx, dy = loc.x - ego_loc.x, loc.y - ego_loc.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist < RAIO_ADAS and dx * fwd.x + dy * fwd.y > 0:
            veiculos.append(round(dist, 1))
            azimuth = round(math.degrees(math.atan2(dy, dx)), 1)
            lidar_objects.append({'class': 'vehicle', 'distance_m': round(dist, 1), 'azimuth_deg': azimuth})

    for a in world.get_actors().filter('walker.*'):
        loc = a.get_location()
        dx, dy = loc.x - ego_loc.x, loc.y - ego_loc.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist < RAIO_ADAS and dx * fwd.x + dy * fwd.y > 0:
            pedestres.append(round(dist, 1))
            azimuth = round(math.degrees(math.atan2(dy, dx)), 1)
            lidar_objects.append({'class': 'pedestrian', 'distance_m': round(dist, 1), 'azimuth_deg': azimuth})

    for a in world.get_actors().filter('traffic.traffic_light*'):
        loc = a.get_location()
        dx, dy = loc.x - ego_loc.x, loc.y - ego_loc.y
        dist = math.sqrt(dx**2 + dy**2)
        if dist < 30.0:
            semaforos.append(round(dist, 1))

    todos = veiculos + pedestres
    return {
        'adas_veiculo':    len(veiculos)  > 0,
        'adas_pedestre':   len(pedestres) > 0,
        'adas_semaforo':   len(semaforos) > 0,
        'dist_frente_m':   min(veiculos)  if veiculos  else None,
        'dist_pedestre_m': min(pedestres) if pedestres else None,
        'n_veiculos':      len(veiculos),
        'n_pedestres':     len(pedestres),
        'lidar_nearest_m': round(min(todos), 1) if todos else None,
        'lidar_objects':   lidar_objects,
    }


def _ler_telemetria(veiculo, sensores, world):
    ctrl  = veiculo.get_control()
    vel   = veiculo.get_velocity()
    rot   = veiculo.get_transform().rotation
    dados = {
        'velocidade_kmh': round(3.6 * math.sqrt(vel.x**2 + vel.y**2 + vel.z**2), 2),
        'throttle':       round(ctrl.throttle, 3),
        'brake':          round(ctrl.brake,    3),
        'steering':       round(ctrl.steer,    3),
        'marcha_re':      ctrl.reverse,
        'gear':           ctrl.gear,
        # orientação (para GNSS heading e IMU roll/pitch/yaw)
        'heading_deg':    round(rot.yaw % 360.0, 1),
        'roll_deg':       round(rot.roll,  2),
        'pitch_deg':      round(rot.pitch, 2),
        'yaw_deg':        round(rot.yaw,   2),
        # sensores (preenchidos abaixo)
        'latitude':  None, 'longitude': None, 'altitude': None,
        'acel_x': None, 'acel_y': None, 'acel_z': None,
        'giro_x': None, 'giro_y': None, 'giro_z': None,
        'lidar_pontos': None, 'lidar_nearest_m': None, 'lidar_objects': [],
        'adas_veiculo': False, 'adas_pedestre': False, 'adas_semaforo': False,
        'dist_frente_m': None, 'dist_pedestre_m': None,
        'n_veiculos': 0, 'n_pedestres': 0,
    }

    gnss = sensores['gnss'].get('dado')
    if gnss:
        dados.update({
            'latitude':  round(gnss.latitude,  6),
            'longitude': round(gnss.longitude, 6),
            'altitude':  round(gnss.altitude,  2),
        })

    imu = sensores['imu'].get('dado')
    if imu:
        a, g = imu.accelerometer, imu.gyroscope
        dados.update({
            'acel_x': round(a.x, 4), 'acel_y': round(a.y, 4), 'acel_z': round(a.z, 4),
            'giro_x': round(g.x, 4), 'giro_y': round(g.y, 4), 'giro_z': round(g.z, 4),
        })

    lidar = sensores['lidar'].get('dado')
    if lidar:
        dados['lidar_pontos'] = len(lidar)
        dados['lidar_pts_xy'] = sensores['lidar'].get('pts_xy')

    dados.update(_adas_ground_truth(world, veiculo))
    return dados


def _limpar(world, veiculo, sensores, npcs):
    logging.info('Encerrando simulacao...')
    for s in sensores.values():
        s['ator'].stop()
        s['ator'].destroy()
    veiculo.destroy()
    for npc in npcs:
        try:
            npc.destroy()
        except Exception:
            pass


def _recriar_atores(world, tm, frequencia, num_npcs):
    for a in world.get_actors().filter('vehicle.*'):
        a.destroy()
    for a in world.get_actors().filter('sensor.*'):
        a.stop()
        a.destroy()
    world.tick()
    veiculo  = _spawnar_ego(world, tm)
    npcs     = _spawnar_npcs(world, tm, num_npcs)
    sensores = _adicionar_sensores(world, veiculo, frequencia)
    return veiculo, npcs, sensores


# ── Loop principal ────────────────────────────────────────────────────────────

def game_loop(args):
    pygame.init()
    pygame.font.init()

    client = carla.Client(args.host, args.port)
    client.set_timeout(60.0)
    logging.info('Conectado ao CARLA %s', client.get_server_version())

    world    = _configurar_mundo(client, args.map, args.fps)
    tm       = _criar_traffic_manager(client)
    veiculo  = _spawnar_ego(world, tm)
    npcs     = _spawnar_npcs(world, tm, args.npcs)
    sensores = _adicionar_sensores(world, veiculo, args.fps)
    hud      = HUD()

    bridge_sender.start()

    velocidade_sim = 1
    dados = {}
    tick  = 0
    total = args.duration * args.fps

    logging.info('Aquecendo trafego (3s)...')
    for _ in range(3 * args.fps):
        world.tick()

    logging.info('Iniciando — %ds | SPACE=pause  R=restart  +/-=velocidade  ESC=sair', args.duration)

    try:
        while tick < total:
            continuar, acao = hud.processar_eventos()
            if not continuar or acao == ACAO_SAIR:
                break

            if acao == ACAO_REINICIAR:
                veiculo, npcs, sensores = _recriar_atores(world, tm, args.fps, args.npcs)
                tick  = 0
                dados = {}
                continue

            if acao == ACAO_MAIS_VEL:
                velocidade_sim = min(velocidade_sim * 2, 8)
            if acao == ACAO_MENOS_VEL:
                velocidade_sim = max(velocidade_sim // 2, 1)

            if hud.pausado:
                hud.renderizar(dados, tick, args.duration, args.fps, velocidade_sim)
                continue

            for _ in range(velocidade_sim):
                if tick >= total:
                    break
                world.tick()
                dados = _ler_telemetria(veiculo, sensores, world)
                tick += 1

            # publica telemetria na rede SOME/IP via bridge TCP
            bridge_sender.enviar(dados)
            hud.bridge_ok = True


            # espectador segue o ego
            t   = veiculo.get_transform()
            fwd = t.get_forward_vector()
            world.get_spectator().set_transform(carla.Transform(
                t.location + carla.Location(x=-8 * fwd.x, y=-8 * fwd.y, z=4),
                carla.Rotation(pitch=-15, yaw=t.rotation.yaw)
            ))

            hud.renderizar(dados, tick, args.duration, args.fps, velocidade_sim)

            if tick % args.fps == 0:
                seg  = tick // args.fps
                dist = dados.get('dist_frente_m')
                logging.info(
                    't=%03ds [%dx] | vel=%5.1f km/h | dist=%s | veic=%d | ped=%d',
                    seg, velocidade_sim, dados.get('velocidade_kmh', 0),
                    f'{dist}m' if dist else 'livre',
                    dados.get('n_veiculos', 0), dados.get('n_pedestres', 0),
                )

    except KeyboardInterrupt:
        pass
    finally:
        hud.fechar()
        _limpar(world, veiculo, sensores, npcs)

        # restaura modo assincrono
        settings = world.get_settings()
        settings.synchronous_mode    = False
        settings.fixed_delta_seconds = None
        world.apply_settings(settings)


# ── Argparse ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description='CARLA SOME/IP Dataset Generator')
    parser.add_argument('--host',     default='127.0.0.1', help='IP do servidor CARLA (padrao: 127.0.0.1)')
    parser.add_argument('--port',     default=2000, type=int, help='Porta TCP do CARLA (padrao: 2000)')
    parser.add_argument('--map',      default='Town10HD_Opt', help='Mapa CARLA (padrao: Town10HD_Opt)')
    parser.add_argument('--duration', default=180, type=int,  help='Duracao da simulacao em segundos (padrao: 180)')
    parser.add_argument('--fps',      default=20,  type=int,  help='Hz do modo sincrono (padrao: 20)')
    parser.add_argument('--npcs',     default=30,  type=int,  help='Numero de NPCs (padrao: 30)')
    parser.add_argument('--bridge-host', default='localhost', dest='bridge_host',
                        help='Host do container ecu_bridge (padrao: localhost)')
    parser.add_argument('--bridge-port', default=5000, type=int, dest='bridge_port',
                        help='Porta TCP do ecu_bridge (padrao: 5000)')
    parser.add_argument('-v', '--verbose', action='store_true')
    args = parser.parse_args()

    logging.basicConfig(
        format='%(levelname)s: %(message)s',
        level=logging.DEBUG if args.verbose else logging.INFO,
    )

    # configura bridge antes de iniciar
    bridge_sender.BRIDGE_HOST = args.bridge_host
    bridge_sender.BRIDGE_PORT = args.bridge_port

    try:
        game_loop(args)
    except KeyboardInterrupt:
        print('\nCancelado pelo usuario.')


if __name__ == '__main__':
    main()
