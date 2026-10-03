#!/usr/bin/env python3
"""Montagem sincronizada — "A fuga de Alcatraz" em colagem de papel.

Uso:
    python3 montagem.py --src PASTA_COM_OS_ARQUIVOS [--out alcatraz_final.mp4] [--work _trabalho]

Requer ffmpeg e ffprobe (>= 5, com libx264 e libsoxr) no PATH e Python 3.8+.
Tudo o que é ajustável está no bloco CONFIGURAÇÃO. O script:
  1. calcula a linha do tempo a partir dos inícios de frase da narração;
  2. renderiza cada trecho de clipe (velocidade por duplicação/descarte de quadros,
     sem interpolação; congela o último quadro quando precisaria passar de 0,67x);
  3. junta os trechos, aplica abertura (quadro parado + fade-in) e final (fade-out);
  4. mixa narração + trilha com ducking, calibra a trilha para ficar N dB abaixo da voz
     durante a fala e normaliza para -14 LUFS / -1,5 dBTP;
  5. imprime o mapa de corte, os avisos e as medições, e gera uma folha de revisão.
"""
from __future__ import annotations

import argparse
import math
import re
import subprocess
import sys
from pathlib import Path

# ============================ CONFIGURAÇÃO ============================

FPS = 24
INTRO_S = 1.5          # quadro parado antes da narração começar
FADE_IN_S = 1.0        # fade-in de vídeo e música na abertura
OUTRO_S = 3.5          # duração depois da última palavra
FADE_OUT_S = 2.5       # fade-out final de vídeo e música
LEAD_FRAMES = 2        # cada corte cai N quadros antes do início da frase

SPEED_MIN, SPEED_MAX = 0.67, 1.33   # abaixo de SPEED_MIN congela o último quadro
WARN_FREEZE_S = 3.0
WARN_MIN_SEG_S = 2.5

# Arquivos de entrada, procurados por padrão dentro de --src
CLIPS = {
    "C01": "*20261003151242.mp4",  # remo + colete
    "C02": "*20261003151247.mp4",  # colher, grade, furadeira
    "C03": "*20261003151253.mp4",  # Alcatraz + bote com três homens
    "C04": "*20261003151300.mp4",  # três fotos, MORRIS E ANGLIN
    "C05": "*20261003151306.mp4",  # cama, cabeça falsa, SABONETE
    "C06": "*20261003151312.mp4",  # grade com cadeado, ANO 1963
    "C07": "*20261003151319.mp4",  # ilha com farol, alfinete no mar
    "C08": "*20261003151327.mp4",  # guarda + calendário, 12 DE JUNHO
    "C09": "*20261003151335.mp4",  # riscos, 14 TENTATIVAS
    "C10": "*20261003151349.mp4",  # capas de chuva, ARQUIVO
}
NARRATION = "*Generated_Audio*.wav"
MUSIC = "*honor-and-sword*.mp3"

# Inícios de frase na narração (s): silencedetect -35 dB / 0,15 s, conferido com a transcrição
SENTENCES = {
    1: (0.212, "12 de junho de 1962, Alcatraz, Baía de São Francisco."),
    2: (6.162, "Na ronda da manhã, um guarda chama um preso."),
    3: (9.345, "A cabeça na cama é falsa, feita de papel, sabão e cabelo humano."),
    4: (14.167, "Frank Morris e os irmãos John e Clarence Anglin tinham sumido."),
    5: (18.437, "Durante meses, eles cavaram atrás das celas com colheres e uma broca improvisada."),
    6: (23.623, "Colaram dezenas de capas de chuva pra fazer um bote."),
    7: (27.081, "Um quarto homem, Allen West, não conseguiu sair a tempo."),
    8: (30.605, "Na noite anterior, os três remaram pela baía, de água gelada e correnteza forte."),
    9: (36.092, "Dias depois, a polícia encontra um remo e pedaços de um colete salva-vidas."),
    10: (40.968, "Em 29 anos, o presídio federal registrara 14 tentativas de fuga."),
    11: (46.244, "Oficialmente, nenhuma havia dado certo."),
    12: (48.992, "Em 1963, Alcatraz fecha."),
    13: (52.222, "Em 1979, o FBI encerra o caso e conclui que os três provavelmente se afogaram."),
    14: (58.632, "Nenhum dos três corpos jamais foi encontrado."),
}
LAST_WORD_END = 60.855

# Plano de corte: (primeira frase coberta, clipe, quadro inicial, quadro final inclusive, nota)
# O trecho vai do início dessa frase até o início da frase do item seguinte.
PLAN = [
    (1, "C07", 46, 191, "ilha, farol e alfinete — abertura"),
    (2, "C08", 120, 191, "guarda diante da cela + 12 DE JUNHO"),
    (3, "C05", 76, 191, "cabeça falsa + SABONETE"),
    (4, "C04", 22, 64, "cortiça vazia → três fotos → MORRIS E ANGLIN; evita o flash (0–20) e 'Prak odanline' (66+)"),
    (5, "C02", 67, 191, "colher, grade, furadeira"),
    (6, "C10", 80, 191, "capas de chuva; evita o jornal falso (até ~79); cobre também a frase 7 (Allen West, sem clipe)"),
    (8, "C03", 61, 191, "bote com os três"),
    (9, "C01", 38, 191, "remo e colete chegando"),
    (10, "C09", 7, 191, "riscos + 14 TENTATIVAS; cobre a frase 11; evita o flash da imagem pronta (0–6)"),
    (12, "C06", 115, 191, "grade + ANO 1963"),
    (13, "C03", 38, 191, "REUSO — não há clipe para FBI/1979"),
    (14, "C07", 94, 191, "REUSO — fechamento em câmera lenta"),
]

# Remendos de papel liso sobre texto ruim: copia o retângulo (sx, sy) do mesmo quadro para (x, y).
# O retângulo cobre a tira + sombra com folga maior que a borda suave, senão o contorno reaparece.
# desde = quadro do clipe a partir do qual o remendo entra (antes disso algo passa por cima da área).
PATCHES = {
    "C07": [
        # "Thousaeng ws a baclar, mislated piecoporn bay"
        dict(x=79, y=59, w=358, h=48, sx=79, sy=109, borda=5),
        # "The offer were ment to coate a lamm in land." — o carimbo cobre a área até o quadro 105;
        # borda inferior seca, alinhada ao topo da fita adesiva (y=651)
        dict(x=849, y=604, w=374, h=48, sx=469, sy=612, borda=4, borda_inferior=False, desde=106),
    ],
}

MUSIC_START_S = 10.0          # a faixa tem ~2 s de silêncio e só ganha corpo perto dos 10 s
MUSIC_UNDER_VOICE_DB = 12.0   # voz − música durante a fala, já com o ducking
DUCK_THRESHOLD, DUCK_RATIO, DUCK_ATTACK_MS, DUCK_RELEASE_MS = 0.02, 8, 40, 600
# Chave do ducking. Com DUCK_HOLD_S = 0 a chave é a própria narração (literal) — medido: a música
# fica ~20 dB abaixo nas palavras e sobe 12–17 dB em cada pausa de 0,5–1 s (bombeamento).
# Com DUCK_HOLD_S > 0 a chave é o envelope fala/pausa da narração (silencedetect), com pausas
# menores que DUCK_HOLD_S preenchidas: profundidade constante de DUCK_DEPTH_DB enquanto houver
# narração; a música só sobe na abertura e no final.
DUCK_HOLD_S = 1.2
DUCK_PREROLL_S = 0.1          # a chave liga um pouco antes da primeira sílaba
DUCK_DEPTH_DB = 8.0           # quanto a música desce sob a voz (define o quanto ela sobe na abertura/final)
SILENCE_DB, SILENCE_MIN_S = -35, 0.15
TARGET_I, TARGET_TP = -14.0, -1.5
LIMITER_DB = -2.3             # teto inicial do limitador (sobreamostrado 4x); baixa sozinho se o AAC passar do pico

VIDEO_CRF = 18
AUDIO_BITRATE = "192k"
SAMPLE_RATE = 48000

# ======================================================================


def run(cmd: list[str], capture: bool = False) -> str:
    print("  $", " ".join(cmd[:6]), "…" if len(cmd) > 6 else "")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.stderr.write(res.stderr[-4000:])
        raise SystemExit(f"falhou: {' '.join(cmd)}")
    return res.stderr if capture else ""


def find(src: Path, pattern: str) -> Path:
    hits = sorted(src.glob(pattern))
    if len(hits) != 1:
        raise SystemExit(f"esperava 1 arquivo para {pattern!r} em {src}, achei {len(hits)}")
    return hits[0]


def loudness(path: Path, start: float | None = None, dur: float | None = None, pre: str = "") -> dict:
    cmd = ["ffmpeg", "-hide_banner", "-nostats"]
    if start is not None:
        cmd += ["-ss", f"{start}"]
    if dur is not None:
        cmd += ["-t", f"{dur}"]
    cmd += ["-i", str(path), "-af", f"{pre}ebur128=peak=true", "-f", "null", "-"]
    err = run(cmd, capture=True)
    summary = err[err.rfind("Summary:"):]
    i = float(re.search(r"I:\s+(-?[\d.]+|-inf) LUFS", summary).group(1))
    tp = float(re.search(r"Peak:\s+(-?[\d.]+|-inf) dBFS", summary).group(1))
    lra = float(re.search(r"LRA:\s+(-?[\d.]+) LU", summary).group(1))
    return {"I": i, "TP": tp, "LRA": lra}


def count_frames(path: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                          "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout.strip()
    return int(out)


def fmt(t: float) -> str:
    return f"{t:6.2f}".replace(".", ",")


# --------------------------- linha do tempo ---------------------------

def timeline() -> tuple[list[dict], int]:
    total = round((INTRO_S + LAST_WORD_END + OUTRO_S) * FPS)
    intro = round(INTRO_S * FPS)
    cuts = [0 if i == 0 else round((INTRO_S + SENTENCES[f][0]) * FPS) - LEAD_FRAMES
            for i, (f, *_rest) in enumerate(PLAN)] + [total]
    segs = []
    for i, (frase, clip, a, b, note) in enumerate(PLAN):
        n = cuts[i + 1] - cuts[i]
        hold = intro if i == 0 else 0
        src = b - a + 1
        speed = src / (n - hold)
        freeze = 0
        warns = []
        if speed < SPEED_MIN:
            speed = SPEED_MIN
            freeze = (n - hold) - math.floor(src / speed)
        if speed > SPEED_MAX + 1e-9:
            warns.append(f"velocidade {speed:.2f}x acima de {SPEED_MAX}x — encurte o trecho do clipe")
        if freeze / FPS > WARN_FREEZE_S:
            warns.append(f"congelamento de {freeze / FPS:.1f} s — gerar clipe mais longo")
        if n / FPS < WARN_MIN_SEG_S:
            warns.append(f"trecho de {n / FPS:.1f} s — curto demais")
        last = PLAN[i + 1][0] - 1 if i + 1 < len(PLAN) else max(SENTENCES)
        segs.append(dict(idx=i + 1, frases=list(range(frase, last + 1)), clip=clip, a=a, b=b,
                         start=cuts[i], n=n, hold=hold, speed=speed, freeze=freeze,
                         note=note, warns=warns))
    return segs, total


def print_map(segs: list[dict]) -> None:
    print("\nMAPA DE CORTE")
    print(" #  tempo (s)        frases  clipe  quadros    veloc.  congel.  nota")
    for s in segs:
        t0, t1 = s["start"] / FPS, (s["start"] + s["n"]) / FPS
        fr = "–".join(map(str, (s["frases"][0], s["frases"][-1]))) if len(s["frases"]) > 1 else str(s["frases"][0])
        hold = f"+{s['hold'] / FPS:.1f}s abertura " if s["hold"] else ""
        frz = f"{s['freeze'] / FPS:.2f}s" if s["freeze"] else "—"
        print(f"{s['idx']:2d}  {fmt(t0)}–{fmt(t1)}  {fr:>6}  {s['clip']}   {s['a']:3d}–{s['b']:3d}   "
              f"{s['speed']:.3f}x  {hold}{frz:>6}  {s['note']}")
        for w in s["warns"]:
            print(f"    ⚠ {w}")


# ------------------------------ vídeo ------------------------------

def render_segment(seg: dict, clip_path: Path, out: Path) -> None:
    label = "v0"
    g = f"[0:v]trim=start_frame={seg['a']}:end_frame={seg['b'] + 1},setpts=PTS-STARTPTS[v0]"
    for j, p in enumerate(PATCHES.get(seg["clip"], [])):
        dist = "min(min(X,W-1-X),Y)" if p.get("borda_inferior") is False else "min(min(X,W-1-X),min(Y,H-1-Y))"
        alpha = f"255*clip({dist}/{p['borda']},0,1)"
        start = p.get("desde", 0) - seg["a"]
        enable = f":enable='gte(n,{start})'" if start > 0 else ""
        g += (f";[{label}]split[b{j}][s{j}];"
              f"[s{j}]crop={p['w']}:{p['h']}:{p['sx']}:{p['sy']},format=rgba,"
              f"geq=r='r(X,Y)':g='g(X,Y)':b='b(X,Y)':a='{alpha}'[p{j}];"
              f"[b{j}][p{j}]overlay={p['x']}:{p['y']}{enable}[v{j + 1}]")
        label = f"v{j + 1}"
    pad = f"tpad=stop_mode=clone:stop={seg['n']}"
    if seg["hold"]:
        pad = f"tpad=start_mode=clone:start={seg['hold']}:stop_mode=clone:stop={seg['n']}"
    # setpts + fps: duplica ou descarta quadros inteiros, sem interpolação
    g += (f";[{label}]setpts=PTS/{seg['speed']:.6f},fps={FPS},{pad},"
          f"trim=end_frame={seg['n']},setpts=PTS-STARTPTS,format=yuv420p[out]")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(clip_path), "-filter_complex", g, "-map", "[out]",
         "-an", "-c:v", "libx264", "-preset", "veryfast", "-qp", "0", str(out)])
    got = count_frames(out)
    if got != seg["n"]:
        raise SystemExit(f"trecho {seg['idx']}: {got} quadros, esperado {seg['n']}")


def build_video(segs: list[dict], total: int, src: Path, work: Path) -> Path:
    parts = []
    for s in segs:
        out = work / f"seg{s['idx']:02d}_{s['clip']}.mp4"
        render_segment(s, find(src, CLIPS[s["clip"]]), out)
        parts.append(out)
    lst = work / "concat.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    joined = work / "video_concat.mp4"
    run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(joined)])
    if count_frames(joined) != total:
        raise SystemExit("contagem de quadros da junção não bate")
    return joined


# ------------------------------ áudio ------------------------------

def build_audio(total_s: float, src: Path, work: Path) -> tuple[Path, dict]:
    narr, music = find(src, NARRATION), find(src, MUSIC)
    delay = round(INTRO_S * 1000)
    voice = work / "voz.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(narr), "-af",
         f"aresample={SAMPLE_RATE}:resampler=soxr,pan=stereo|c0=c0|c1=c0,adelay={delay}|{delay},"
         f"apad=whole_dur={total_s},atrim=0:{total_s}", "-c:a", "pcm_f32le", str(voice)])
    bed = work / "trilha.wav"
    run(["ffmpeg", "-v", "error", "-y", "-ss", f"{MUSIC_START_S}", "-t", f"{total_s}", "-i", str(music), "-af",
         f"aresample={SAMPLE_RATE}:resampler=soxr,aformat=channel_layouts=stereo,"
         f"afade=t=in:d={FADE_IN_S},afade=t=out:st={total_s - FADE_OUT_S}:d={FADE_OUT_S},"
         f"apad=whole_dur={total_s},atrim=0:{total_s}", "-c:a", "pcm_f32le", str(bed)])

    speech = (INTRO_S, LAST_WORD_END)  # janela de fala no vídeo final
    v = loudness(voice, *speech)

    key = voice
    if DUCK_HOLD_S > 0:
        key = work / "chave_ducking.wav"
        regions = speech_regions(narr)
        # tom com nível RMS fixo: (nível − limiar) × (1 − 1/ratio) = profundidade desejada
        rms_db = 20 * math.log10(DUCK_THRESHOLD) + DUCK_DEPTH_DB / (1 - 1 / DUCK_RATIO)
        amp = 10 ** (rms_db / 20) * math.sqrt(2)
        gate = "+".join(f"between(t,{a:.3f},{b:.3f})" for a, b in regions)
        run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
             f"aevalsrc=exprs='{amp:.6f}*sin(2*PI*1000*t)*gt({gate},0)':s={SAMPLE_RATE}:d={total_s}",
             "-af", "pan=stereo|c0=c0|c1=c0", "-c:a", "pcm_f32le", str(key)])
    ducking = (f"threshold={DUCK_THRESHOLD}:ratio={DUCK_RATIO}:"
               f"attack={DUCK_ATTACK_MS}:release={DUCK_RELEASE_MS}")

    def duck(gain_db: float, out: Path) -> None:
        run(["ffmpeg", "-v", "error", "-y", "-i", str(bed), "-i", str(key), "-filter_complex",
             f"[0:a]volume={gain_db:.2f}dB[m];[m][1:a]sidechaincompress={ducking}[d]",
             "-map", "[d]", "-c:a", "pcm_f32le", str(out)])

    # O ganho do ducking depende só da voz, então o nível da trilha escala 1:1 com o ganho dela.
    probe = work / "trilha_duck_teste.wav"
    duck(0.0, probe)
    d0 = loudness(probe, *speech)
    gain = (v["I"] - MUSIC_UNDER_VOICE_DB) - d0["I"]
    ducked = work / "trilha_duck.wav"
    duck(gain, ducked)
    d = loudness(ducked, *speech)
    bed_raw = loudness(bed, *speech, pre=f"volume={gain:.2f}dB,")
    pump = momentary_spread(ducked, *speech)

    mix = work / "mix.wav"
    run(["ffmpeg", "-v", "error", "-y", "-i", str(voice), "-i", str(ducked), "-filter_complex",
         "[0:a][1:a]amix=inputs=2:normalize=0:duration=first[a]", "-map", "[a]", "-c:a", "pcm_f32le", str(mix)])
    m = loudness(mix)

    # Normalização: ganho estático + limitador sobreamostrado 4x (aproxima pico real).
    # O ganho é refinado até bater o alvo de loudness; o teto baixa se o AAC passar do pico.
    lim, aac = work / "mix_lim.wav", work / "audio_final.m4a"
    ceiling = LIMITER_DB
    for _ in range(5):
        mgain = TARGET_I - m["I"]
        for _ in range(6):
            run(["ffmpeg", "-v", "error", "-y", "-i", str(mix), "-af",
                 f"volume={mgain:.3f}dB,aresample={SAMPLE_RATE * 4}:resampler=soxr,"
                 f"alimiter=limit={10 ** (ceiling / 20):.5f}:attack=5:release=50:level=0,"
                 f"aresample={SAMPLE_RATE}:resampler=soxr", "-c:a", "pcm_f32le", str(lim)])
            r = loudness(lim)
            if abs(r["I"] - TARGET_I) <= 0.03:
                break
            mgain += TARGET_I - r["I"]
        run(["ffmpeg", "-v", "error", "-y", "-i", str(lim), "-c:a", "aac", "-b:a", AUDIO_BITRATE,
             "-ar", str(SAMPLE_RATE), str(aac)])
        a = loudness(aac)
        if a["TP"] <= TARGET_TP and abs(a["I"] - TARGET_I) <= 0.1:
            break
        ceiling -= max(0.2, a["TP"] - TARGET_TP + 0.1)
    else:
        print("  ⚠ não convergiu para o alvo de loudness/pico — confira as medições")

    stats = {
        "voz_I": v["I"], "trilha_ganho_dB": gain,
        "trilha_sem_ducking_I": bed_raw["I"], "trilha_com_ducking_I": d["I"],
        "diferenca_voz_trilha_dB": v["I"] - d["I"],
        "reducao_ducking_dB": bed_raw["I"] - d["I"],
        "musica_na_fala_mediana_M": pump["p50"],
        "musica_na_fala_subida_p95_dB": pump["p95"] - pump["p50"],
        "mix_antes_I": m["I"], "mix_antes_TP": m["TP"],
        "ganho_master_dB": mgain, "teto_limitador_dB": ceiling,
        **limiter_activity(mix, mgain, ceiling),
    }
    return aac, stats


def speech_regions(narr: Path) -> list[tuple[float, float]]:
    """Trechos com voz (tempo do vídeo final), pausas menores que DUCK_HOLD_S preenchidas."""
    err = run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(narr), "-af",
               f"silencedetect=noise={SILENCE_DB}dB:d={SILENCE_MIN_S}", "-f", "null", "-"], capture=True)
    starts = [float(x) for x in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(x) for x in re.findall(r"silence_end: ([\d.]+)", err)]
    edges = sorted([(s, "s") for s in starts] + [(e, "e") for e in ends])
    regions, cur = [], 0.0
    for t, kind in edges:  # voz = entre um fim de silêncio e o próximo início de silêncio
        if kind == "e":
            cur = t
        elif t > cur:
            regions.append([cur, t])
    if cur < LAST_WORD_END - 0.05:  # narração termina sem silêncio final
        regions.append([cur, LAST_WORD_END])
    merged = []
    for a, b in regions:
        if merged and a - merged[-1][1] < DUCK_HOLD_S:
            merged[-1][1] = b
        else:
            merged.append([a, b])
    return [(max(0.0, a + INTRO_S - DUCK_PREROLL_S), b + INTRO_S) for a, b in merged if b - a > 0.05]


def momentary_spread(path: Path, start: float, dur: float) -> dict:
    """Loudness momentânea (400 ms) da música na janela de fala: mediana e percentil 95."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{start}", "-t", f"{dur}", "-i", str(path), "-af",
                          "ebur128=metadata=1,ametadata=print:key=lavfi.r128.M:file=-", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    vals = sorted(float(x) for x in re.findall(r"lavfi.r128.M=(-?[\d.]+)", out))
    vals = vals[len(vals) // 10:]  # descarta o início da janela de medição (400 ms ainda enchendo)
    return {"p50": vals[len(vals) // 2], "p95": vals[int(len(vals) * 0.95)]}


def limiter_activity(mix: Path, gain_db: float, ceiling: float) -> dict:
    """Quanto o limitador trabalha: pico por janela de 100 ms do mix com ganho, contra o teto."""
    out = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mix), "-af",
                          f"volume={gain_db:.3f}dB,asetnsamples=n={SAMPLE_RATE // 10},astats=metadata=1:reset=1,"
                          "ametadata=print:key=lavfi.astats.Overall.Peak_level:file=-", "-f", "null", "-"],
                         capture_output=True, text=True).stdout
    peaks = [float(x) for x in re.findall(r"Peak_level=(-?[\d.]+)", out)]
    over = [p - ceiling for p in peaks if p > ceiling]
    return {"limitador_janelas_pct": 100 * len(over) / max(1, len(peaks)),
            "limitador_reducao_media_dB": sum(over) / max(1, len(over)),
            "limitador_reducao_max_dB": max(over, default=0.0)}


# ------------------------------ final ------------------------------

def review_sheet(video: Path, segs: list[dict], out: Path, work: Path) -> None:
    tiles = []
    for s in segs:
        for k, f in enumerate((s["start"] + 1, s["start"] + s["n"] // 2, s["start"] + s["n"] - 1)):
            png = work / f"rev_{s['idx']:02d}_{k}.png"
            t = f / FPS
            run(["ffmpeg", "-v", "error", "-y", "-ss", f"{t:.4f}", "-i", str(video), "-frames:v", "1", "-vf",
                 f"scale=426:-2,drawtext=text='{s['idx']} {s['clip']} {t:.2f}s':x=6:y=6:fontsize=18:"
                 "fontcolor=white:box=1:boxcolor=black@0.6", str(png)])
            tiles.append(png)
    args = []
    for p in tiles:
        args += ["-i", str(p)]
    rows = len(segs)
    g = "".join(f"[{i}:v]" for i in range(len(tiles))) + \
        f"xstack=inputs={len(tiles)}:layout=" + "|".join(
            f"{c * 426}_{r * 240}" for r in range(rows) for c in range(3)) + "[o]"
    run(["ffmpeg", "-v", "error", "-y", *args, "-filter_complex", g, "-map", "[o]", "-q:v", "3", str(out)])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, required=True, help="pasta com clipes, narração e trilha")
    ap.add_argument("--out", type=Path, default=Path("alcatraz_final.mp4"))
    ap.add_argument("--work", type=Path, default=Path("_trabalho"))
    ap.add_argument("--so-plano", action="store_true", help="só imprime o mapa de corte")
    args = ap.parse_args()

    segs, total = timeline()
    total_s = total / FPS
    print_map(segs)
    print(f"\nduração final: {total} quadros = {total_s:.3f} s")
    if args.so_plano:
        return
    args.work.mkdir(parents=True, exist_ok=True)

    print("\n[vídeo]")
    video = build_video(segs, total, args.src, args.work)
    print("\n[áudio]")
    audio, stats = build_audio(total_s, args.src, args.work)

    print("\n[codificação final]")
    run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(audio),
         "-vf", f"fade=t=in:st=0:d={FADE_IN_S},fade=t=out:st={total_s - FADE_OUT_S}:d={FADE_OUT_S}",
         "-map", "0:v", "-map", "1:a",
         "-c:v", "libx264", "-preset", "slow", "-crf", str(VIDEO_CRF), "-profile:v", "high",
         "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(args.out)])

    final = loudness(args.out)
    stats.update({"final_I": final["I"], "final_TP": final["TP"], "final_LRA": final["LRA"],
                  "final_quadros": count_frames(args.out)})
    sheet = args.out.with_name(args.out.stem + "_revisao.jpg")
    review_sheet(args.out, segs, sheet, args.work)

    print("\nMEDIÇÕES")
    for k, val in stats.items():
        print(f"  {k}: {val:.2f}" if isinstance(val, float) else f"  {k}: {val}")
    print(f"\nok: {args.out}  |  revisão: {sheet}")


if __name__ == "__main__":
    main()
