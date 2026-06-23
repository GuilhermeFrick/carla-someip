"""
Dashboard de telemetria em tempo real (pygame).

Controles:
  SPACE   — pausar / resumir
  R       — reiniciar simulacao
  +/-     — aumentar / diminuir velocidade (1x .. 8x)
  ESC/Q   — encerrar
"""

import pygame
import math

PRETO     = (10,  10,  10)
BRANCO    = (240, 240, 240)
CINZA     = (60,  60,  60)
CINZA_MED = (120, 120, 120)
VERDE     = (0,   200, 100)
VERMELHO  = (220, 50,  50)
AMARELO   = (255, 200, 0)
AZUL      = (50,  150, 255)
LARANJA   = (255, 140, 0)
ROXO      = (160, 80,  220)

LARGURA = 640
ALTURA  = 660

ACAO_NENHUMA   = 'nenhuma'
ACAO_PAUSAR    = 'pausar'
ACAO_REINICIAR = 'reiniciar'
ACAO_SAIR      = 'sair'
ACAO_MAIS_VEL  = 'mais_vel'
ACAO_MENOS_VEL = 'menos_vel'

# Layout
TOPO_H  = 200   # altura do painel superior (radar + adas)
SEP_Y   = TOPO_H + 32
CTRL_Y  = ALTURA - 34

# Radar
RADAR_CX = 160
RADAR_CY = TOPO_H // 2 + 16
RADAR_R  = 85

# Painel ADAS
ADAS_X = 328


class HUD:
    def __init__(self):
        pygame.init()
        self.tela          = pygame.display.set_mode((LARGURA, ALTURA))
        pygame.display.set_caption('Telemetria CARLA — SOME/IP')
        self.clock         = pygame.time.Clock()
        self.fonte_grande  = pygame.font.SysFont('Consolas', 58, bold=True)
        self.fonte_media   = pygame.font.SysFont('Consolas', 20, bold=True)
        self.fonte_pequena = pygame.font.SysFont('Consolas', 15)
        self.fonte_label   = pygame.font.SysFont('Consolas', 13)
        self.pausado       = False
        self.bridge_ok     = False   # atualizado pelo carla_client

    # ── Eventos ──────────────────────────────────────────────────────────────

    def processar_eventos(self):
        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                return False, ACAO_SAIR
            if evento.type == pygame.KEYDOWN:
                if evento.key in (pygame.K_ESCAPE, pygame.K_q):
                    return False, ACAO_SAIR
                if evento.key == pygame.K_SPACE:
                    self.pausado = not self.pausado
                    return True, ACAO_PAUSAR
                if evento.key == pygame.K_r:
                    self.pausado = False
                    return True, ACAO_REINICIAR
                if evento.key in (pygame.K_PLUS, pygame.K_EQUALS, pygame.K_KP_PLUS):
                    return True, ACAO_MAIS_VEL
                if evento.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    return True, ACAO_MENOS_VEL
        return True, ACAO_NENHUMA

    # ── Primitivas ───────────────────────────────────────────────────────────

    def _barra(self, x, y, w, h, valor, cor, label=''):
        pygame.draw.rect(self.tela, CINZA, (x, y, w, h), border_radius=4)
        fill = int(w * max(0.0, min(1.0, valor)))
        if fill > 0:
            pygame.draw.rect(self.tela, cor, (x, y, fill, h), border_radius=4)
        pygame.draw.rect(self.tela, CINZA_MED, (x, y, w, h), 1, border_radius=4)
        if label:
            self.tela.blit(self.fonte_label.render(label, True, CINZA_MED), (x, y - 15))
        pct = self.fonte_label.render(f'{valor*100:.0f}%', True, BRANCO)
        self.tela.blit(pct, (x + w + 5, y + 1))

    def _volante(self, cx, cy, raio, angulo_norm):
        pygame.draw.circle(self.tela, CINZA, (cx, cy), raio, 2)
        a  = math.radians(angulo_norm * 90)
        x2 = cx + int(raio * math.sin(a))
        y2 = cy - int(raio * math.cos(a))
        pygame.draw.line(self.tela, AMARELO, (cx, cy), (x2, y2), 3)
        pygame.draw.circle(self.tela, AMARELO, (cx, cy), 4)

    def _velocimetro(self, cx, cy, raio, vel, vel_max=120):
        inicio = 210
        for i in range(241):
            ang = math.radians(inicio + i)
            x   = cx + int(raio * math.cos(ang))
            y   = cy - int(raio * math.sin(ang))
            pygame.draw.circle(self.tela, CINZA, (x, y), 2)

        pct = min(vel / vel_max, 1.0)
        cor = VERDE if pct < 0.6 else (AMARELO if pct < 0.85 else VERMELHO)
        for i in range(int(pct * 240)):
            ang = math.radians(inicio + i)
            x   = cx + int(raio * math.cos(ang))
            y   = cy - int(raio * math.sin(ang))
            pygame.draw.circle(self.tela, cor, (x, y), 3)

        for v in [0, 30, 60, 90, 120]:
            p   = v / vel_max
            ang = math.radians(inicio + p * 240)
            x1  = cx + int((raio - 8)  * math.cos(ang))
            y1  = cy - int((raio - 8)  * math.sin(ang))
            x2  = cx + int((raio + 4)  * math.cos(ang))
            y2  = cy - int((raio + 4)  * math.sin(ang))
            pygame.draw.line(self.tela, CINZA_MED, (x1, y1), (x2, y2), 2)
            lbl = self.fonte_label.render(str(v), True, CINZA_MED)
            lx  = cx + int((raio + 16) * math.cos(ang)) - lbl.get_width()  // 2
            ly  = cy - int((raio + 16) * math.sin(ang)) - lbl.get_height() // 2
            self.tela.blit(lbl, (lx, ly))

    def _botao(self, x, y, texto, ativo=False, cor_ativa=VERDE):
        cor   = cor_ativa if ativo else CINZA
        borda = BRANCO   if ativo else CINZA_MED
        lbl   = self.fonte_label.render(texto, True, BRANCO)
        w, h  = lbl.get_width() + 16, 22
        pygame.draw.rect(self.tela, cor,   (x, y, w, h), border_radius=4)
        pygame.draw.rect(self.tela, borda, (x, y, w, h), 1, border_radius=4)
        self.tela.blit(lbl, (x + 8, y + 4))
        return w

    def _badge(self, x, y, texto, ativo, cor_on, cor_off=CINZA):
        cor = cor_on if ativo else cor_off
        lbl = self.fonte_label.render(texto, True, PRETO if ativo else CINZA_MED)
        w, h = lbl.get_width() + 10, 18
        pygame.draw.rect(self.tela, cor, (x, y, w, h), border_radius=9)
        self.tela.blit(lbl, (x + 5, y + 2))
        return w + 6

    # ── Radar ADAS ───────────────────────────────────────────────────────────

    def _radar(self, dados):
        cx, cy, r = RADAR_CX, RADAR_CY, RADAR_R
        dist      = dados.get('dist_frente_m')
        n_veic    = dados.get('n_veiculos', 0)
        n_ped     = dados.get('n_pedestres', 0)
        raio_real = 50.0

        pygame.draw.circle(self.tela, (20, 20, 30), (cx, cy), r)
        for frac in [0.33, 0.66, 1.0]:
            pygame.draw.circle(self.tela, CINZA, (cx, cy), int(r * frac), 1)
        pygame.draw.line(self.tela, CINZA, (cx, cy - r), (cx, cy + r), 1)
        pygame.draw.line(self.tela, CINZA, (cx - r, cy), (cx + r, cy), 1)

        pygame.draw.polygon(self.tela, CINZA_MED,
                            [(cx, cy - r + 4), (cx - 5, cy - r + 14), (cx + 5, cy - r + 14)])

        pygame.draw.rect(self.tela, VERMELHO, (cx - 5, cy - 9, 10, 18), border_radius=2)

        if dist is not None:
            pct = min(dist / raio_real, 1.0)
            dy  = int(r * pct)
            pygame.draw.rect(self.tela, AZUL, (cx - 5, cy - dy - 9, 10, 14), border_radius=2)
            d_lbl = self.fonte_label.render(f'{dist:.0f}m', True, AZUL)
            self.tela.blit(d_lbl, (cx + 8, cy - dy - 6))

        pygame.draw.rect(self.tela, CINZA, (cx - r, cy + r + 4, r * 2, 1))
        vc = self.fonte_label.render(f'VEI:{n_veic}', True, AZUL)
        pe = self.fonte_label.render(f'PED:{n_ped}', True, LARANJA)
        self.tela.blit(vc, (cx - r,     cy + r + 8))
        self.tela.blit(pe, (cx,          cy + r + 8))

        pygame.draw.circle(self.tela, CINZA_MED, (cx, cy), r, 1)
        lbl = self.fonte_label.render('ADAS RADAR  50m', True, CINZA_MED)
        self.tela.blit(lbl, (cx - lbl.get_width() // 2, cy - r - 16))

    # ── Painel ADAS (direita) ─────────────────────────────────────────────────

    def _painel_adas(self, dados):
        x0 = ADAS_X
        y0 = 28
        w  = LARGURA - x0 - 8
        h  = TOPO_H + 4

        pygame.draw.rect(self.tela, (20, 20, 30), (x0, y0, w, h), border_radius=6)
        pygame.draw.rect(self.tela, CINZA,         (x0, y0, w, h), 1, border_radius=6)

        titulo = self.fonte_label.render('DETECCAO  ADAS', True, CINZA_MED)
        self.tela.blit(titulo, (x0 + 8, y0 + 8))

        dist = dados.get('dist_frente_m')
        if dist is not None:
            cor_d = VERDE if dist > 15 else (AMARELO if dist > 8 else VERMELHO)
            d_val = self.fonte_media.render(f'{dist:.1f} m', True, cor_d)
            d_lbl = self.fonte_label.render('dist. veiculo frente', True, CINZA_MED)
            self.tela.blit(d_val, (x0 + 8, y0 + 28))
            self.tela.blit(d_lbl, (x0 + 8, y0 + 52))
        else:
            nd = self.fonte_media.render('livre', True, VERDE)
            nl = self.fonte_label.render('nenhum veiculo proximo', True, CINZA_MED)
            self.tela.blit(nd, (x0 + 8, y0 + 28))
            self.tela.blit(nl, (x0 + 8, y0 + 52))

        by = y0 + 78
        self.tela.blit(self.fonte_label.render('Em alcance (50m):', True, CINZA_MED), (x0 + 8, by))
        by += 20
        bx = x0 + 8
        bx += self._badge(bx, by, 'VEICULO',  dados.get('adas_veiculo',  False), AZUL)
        bx += self._badge(bx, by, 'PEDESTRE', dados.get('adas_pedestre', False), LARANJA)
        by += 26
        bx = x0 + 8
        self._badge(bx, by, 'SEMAFORO', dados.get('adas_semaforo', False), AMARELO)

        by += 28
        n_v = dados.get('n_veiculos', 0)
        n_p = dados.get('n_pedestres', 0)
        self.tela.blit(
            self.fonte_pequena.render(f'Veiculos: {n_v}', True, AZUL), (x0 + 8, by))
        self.tela.blit(
            self.fonte_pequena.render(f'Pedestres: {n_p}', True, LARANJA), (x0 + 8, by + 18))

        lidar = dados.get('lidar_pontos')
        if lidar:
            li = self.fonte_label.render(f'LiDAR  {lidar} pts', True, CINZA_MED)
            self.tela.blit(li, (x0 + 8, y0 + h - 22))

        gt = self.fonte_label.render('ground truth', True, (60, 60, 80))
        self.tela.blit(gt, (x0 + w - gt.get_width() - 6, y0 + h - 16))

    # ── Indicador SOME/IP bridge ──────────────────────────────────────────────

    def _bridge_status(self):
        cor  = VERDE if self.bridge_ok else VERMELHO
        txt  = 'SOME/IP OK' if self.bridge_ok else 'SOME/IP --'
        lbl  = self.fonte_label.render(txt, True, cor)
        dot_x = LARGURA - lbl.get_width() - 24
        dot_y = 10
        pygame.draw.circle(self.tela, cor, (dot_x - 6, dot_y + 5), 4)
        self.tela.blit(lbl, (dot_x, dot_y))

    # ── Overlay pause ─────────────────────────────────────────────────────────

    def _overlay_pause(self):
        ov = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 150))
        self.tela.blit(ov, (0, 0))
        txt = self.fonte_media.render('PAUSADO', True, AMARELO)
        sub = self.fonte_label.render('SPACE para resumir', True, CINZA_MED)
        self.tela.blit(txt, (LARGURA // 2 - txt.get_width() // 2, ALTURA // 2 - 18))
        self.tela.blit(sub, (LARGURA // 2 - sub.get_width() // 2, ALTURA // 2 + 14))

    # ── Render principal ──────────────────────────────────────────────────────

    def renderizar(self, dados, tick, duracao, frequencia, velocidade_sim=1):
        self.tela.fill(PRETO)

        vel      = dados.get('velocidade_kmh', 0) or 0
        throttle = dados.get('throttle', 0) or 0
        brake    = dados.get('brake', 0) or 0
        steering = dados.get('steering', 0) or 0
        lat      = dados.get('latitude')
        lon      = dados.get('longitude')
        acel_x   = dados.get('acel_x') or 0
        acel_y   = dados.get('acel_y') or 0
        acel_z   = dados.get('acel_z') or 0
        seg      = tick // frequencia

        # barra de progresso
        prog = tick / max(duracao * frequencia, 1)
        pygame.draw.rect(self.tela, CINZA,   (0, 0, LARGURA, 6))
        pygame.draw.rect(self.tela, AMARELO, (0, 0, int(LARGURA * prog), 6))
        self.tela.blit(
            self.fonte_label.render('CARLA  SOME/IP', True, CINZA_MED), (8, 10))
        self.tela.blit(
            self.fonte_label.render(f't={seg:03d}s/{duracao}s  [{velocidade_sim}x]',
                                    True, CINZA_MED), (LARGURA - 200, 10))

        # status bridge
        self._bridge_status()

        # radar ADAS
        self._radar(dados)

        # painel ADAS direita
        self._painel_adas(dados)

        # separador
        pygame.draw.line(self.tela, CINZA, (0, SEP_Y), (LARGURA, SEP_Y))

        # velocimetro
        VEL_CX, VEL_CY, VEL_R = 200, SEP_Y + 150, 105
        self._velocimetro(VEL_CX, VEL_CY, VEL_R, vel)
        vel_txt = self.fonte_grande.render(f'{vel:.0f}', True, BRANCO)
        self.tela.blit(vel_txt, (VEL_CX - vel_txt.get_width() // 2, VEL_CY - 34))
        kmh = self.fonte_label.render('km/h', True, CINZA_MED)
        self.tela.blit(kmh, (VEL_CX - kmh.get_width() // 2, VEL_CY + 76))

        # volante
        self._volante(VEL_CX, VEL_CY + 118, 26, steering)
        st_lbl = self.fonte_label.render(f'steer {steering:+.2f}', True, CINZA_MED)
        self.tela.blit(st_lbl, (VEL_CX - st_lbl.get_width() // 2, VEL_CY + 150))

        # throttle / brake
        bx, bw, bh = 30, 160, 14
        by = SEP_Y + 14
        self._barra(bx, by,      bw, bh, throttle, VERDE,    'THROTTLE')
        self._barra(bx, by + 38, bw, bh, brake,    VERMELHO, 'BRAKE')

        # IMU
        ix = ADAS_X
        self.tela.blit(self.fonte_label.render('IMU (m/s²)', True, CINZA_MED), (ix, SEP_Y + 10))
        for i, (e, v) in enumerate([('X', acel_x), ('Y', acel_y), ('Z', acel_z)]):
            cor = AZUL if abs(v) < 5 else LARANJA
            self.tela.blit(
                self.fonte_pequena.render(f'{e}: {v:+7.2f}', True, cor),
                (ix, SEP_Y + 26 + i * 18))

        # GNSS
        gy = SEP_Y + 96
        self.tela.blit(self.fonte_label.render('GNSS', True, CINZA_MED), (30, gy))
        self.tela.blit(
            self.fonte_pequena.render(f'Lat: {lat:.6f}' if lat else 'Lat: --', True, AZUL),
            (30, gy + 16))
        self.tela.blit(
            self.fonte_pequena.render(f'Lon: {lon:.6f}' if lon else 'Lon: --', True, AZUL),
            (30, gy + 32))

        # barra de controles
        pygame.draw.line(self.tela, CINZA, (0, CTRL_Y - 6), (LARGURA, CTRL_Y - 6))
        cx = 10
        label_pp = '▶ PLAY ' if self.pausado else '⏸ PAUSE'
        cor_pp   = VERDE if self.pausado else AMARELO
        cx += self._botao(cx, CTRL_Y, label_pp, ativo=True, cor_ativa=cor_pp) + 6
        cx += self._botao(cx, CTRL_Y, '↺ RESTART', cor_ativa=AZUL) + 6
        cx += self._botao(cx, CTRL_Y, f'⚡ {velocidade_sim}x',
                          ativo=velocidade_sim > 1, cor_ativa=ROXO) + 6
        self._botao(cx, CTRL_Y, '✕ SAIR', cor_ativa=VERMELHO)
        atalhos = self.fonte_label.render('SPACE · R · +/- · ESC', True, CINZA)
        self.tela.blit(atalhos, (LARGURA - atalhos.get_width() - 8, CTRL_Y + 4))

        if self.pausado:
            self._overlay_pause()

        pygame.display.flip()
        self.clock.tick(frequencia)

    def fechar(self):
        pygame.quit()
