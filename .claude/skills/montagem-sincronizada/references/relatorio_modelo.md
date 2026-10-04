# Modelo de RELATORIO.md

Preencha com os dados do projeto. Seja curto e específico: tempo no vídeo, clipe, número medido. Apague as seções que não se aplicam, menos "Pontos fracos". Se não houver nenhum, diga isso explicitamente.

```markdown
# <Título do vídeo>

## Arquivos

| Arquivo | O que é |
|---|---|
| `<nome>.mp4` | <largura>×<altura>, <fps> fps, H.264 High (CRF 18), AAC 192 kbps 48 kHz estéreo, +faststart. <duração> s (<quadros> quadros), <MB> MB. |
| `<nome>_revisao.jpg` | Início, meio e fim de cada trecho. |
| `plano.json` + `montagem.py` | Para refazer: `python3 montagem.py render plano.json`. O plano define os cortes, os remendos e os ajustes de vídeo e áudio. |
| `medicoes.json`, `mapa_de_corte.md` | Números e mapa gerados pelo render. |

## Mapa de corte final
<colar mapa_de_corte.md>

## Áudio: medições
- Fontes: narração <X> LUFS (<mono/estéreo>), trilha <Y> LUFS, pico <Z> dBTP <(clipada na origem?)>, usada a partir de <s> s.
- Música sob a voz: <voz_menos_trilha_dB> dB abaixo; variação sob a voz <p95−p5> dB; ducking <modo>, profundidade <dB>.
- Abertura e final: a música sobe até <dB> do nível da voz.
- Mixagem final: <final_I> LUFS, <final_TP> dBTP, LRA <final_LRA>.
- Limitador: atua em <pct>% das janelas de 100 ms, média de <dB>, máximo de <dB>.
- Avaliação feita só por medição; o áudio não foi ouvido.

## Onde me afastei do pedido literal, e por quê
1. <desvio — motivo — como voltar ao literal>

## Pontos fracos que ficaram
### Falta de imagem
- Frase <n> (<tema>): <solução usada>, <por que é fraca>.
### Trechos esticados, acelerados ou congelados
- Trecho <i> (<clipe>): <vel>x + <s> s congelado — <motivo>.
### Erros de texto e de conteúdo visíveis
- <clipe>, <t0–t1 s no vídeo>: <o que aparece>.
### Áudio
- <limitador, clipping da origem, taxa da narração, caráter da trilha não avaliado>
### Licença da trilha
- <origem, condições, risco de Content ID, o que guardar>

## Clipes novos que valem a pena (em ordem de prioridade)
1. <frase / duração>: <descrição sem ambiguidade>; nenhum texto legível.
```
