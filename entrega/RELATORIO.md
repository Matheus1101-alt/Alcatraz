# Alcatraz — montagem em colagem de papel

## Arquivos

| Arquivo | O que é |
|---|---|
| `alcatraz_final.mp4` | 1280×720, 24 fps, H.264 High (CRF 18), AAC 192 kbps 48 kHz estéreo, `+faststart`. 65,875 s (1581 quadros), 28,5 MB. |
| `montagem.py` | Refaz tudo a partir dos arquivos originais. Os ajustes ficam no bloco `CONFIGURAÇÃO`. |
| `alcatraz_final_revisao.jpg` | Início, meio e fim de cada trecho, para conferir os cortes. |

Para refazer: `python3 montagem.py --src PASTA_COM_OS_ARQUIVOS`. Para ver só o mapa de corte: acrescente `--so-plano`. É preciso ter ffmpeg 5 ou mais recente, com libx264 e libsoxr.

## Mapa de corte final

A narração começa em 1,5 s. Cada corte cai 2 quadros antes do início da frase seguinte. Os quadros indicados são do clipe de 8 s (192 quadros, de 0 a 191).

| # | Tempo | Frase(s) | Clipe | Quadros usados | Velocidade | Congelamento |
|---|---|---|---|---|---|---|
| 1 | 0,00–7,58 | 1 (12 de junho, Alcatraz) | C07 ilha e farol | 46–191 | 1,00x | 1,5 s de abertura, com fade-in |
| 2 | 7,58–10,75 | 2 (guarda) | C08 guarda e calendário | 120–191 | 0,95x | — |
| 3 | 10,75–15,58 | 3 (cabeça falsa) | C05 cama e SABONETE | 76–191 | 1,00x | — |
| 4 | 15,58–19,83 | 4 (Morris e Anglin) | C04 três fotos | 22–64 | 0,67x | 1,58 s |
| 5 | 19,83–25,04 | 5 (colheres e broca) | C02 colher e furadeira | 67–191 | 1,00x | — |
| 6 | 25,04–32,04 | 6 e 7 (capas; Allen West) | C10 capas de chuva | 80–191 | 0,67x | 0,04 s |
| 7 | 32,04–37,50 | 8 (remaram) | C03 bote e Alcatraz | 61–191 | 1,00x | — |
| 8 | 37,50–42,38 | 9 (remo e colete) | C01 remo e colete | 38–191 | 1,32x | — |
| 9 | 42,38–50,42 | 10 e 11 (14 tentativas) | C09 riscos | 7–191 | 0,96x | — |
| 10 | 50,42–53,62 | 12 (1963) | C06 grade e ANO 1963 | 115–191 | 1,00x | — |
| 11 | 53,62–60,04 | 13 (FBI, 1979) | C03 **repetido** | 38–191 | 1,00x | — |
| 12 | 60,04–65,88 | 14 + final | C07 **repetido** | 94–191 | 0,70x | — (fade-out de 2,5 s) |

## Áudio: medições

- **Fontes:** a narração tem -20,9 LUFS em mono (-17,9 LUFS em estéreo). A trilha tem -10,8 LUFS e pico de +0,2 dBTP, ou seja, já vem com clipping. Ela foi usada a partir dos 10 s, porque antes disso tem silêncio e fica fraca.
- **Música sob a voz:** fica 12,0 dB abaixo (integrado na janela da fala) e 10,8 dB abaixo durante as palavras (mediana em janelas de 400 ms).
- **Ducking:** reduz a música em 10 dB. Nas pausas entre frases ela varia de -2 a +2,4 dB, que é a dinâmica da própria faixa, sem bombeamento.
- **Abertura e final:** na abertura a música fica 4,5 dB abaixo do nível da voz. No final ela sobe até 0,3 dB abaixo desse nível antes do fade-out.
- **Mixagem final:** -14,0 LUFS, -1,9 dBTP, LRA de 4,2 LU.
- **Limitador:** atua em 24% das janelas de 100 ms, com redução média de 2,3 dB e máxima de 5,8 dB.

## Onde me afastei do prompt literal, e por quê

1. **Chave do ducking.** Os parâmetros são os pedidos: 0,02 / 8 / 40 ms / 600 ms. Mas a chave não é a narração crua, e sim o envelope de fala e pausa dela, com as pausas menores que 1,2 s preenchidas. Com a narração crua, medi a música 20 dB abaixo durante as palavras e subindo de 12 a 17 dB em **cada** pausa de 0,5 a 1 s, um bombeamento evidente. Para voltar ao comportamento literal, use `DUCK_HOLD_S = 0`.
2. **Normalização.** Usei ganho estático e um limitador sobreamostrado 4x no lugar do `loudnorm`. O `loudnorm` caiu no modo dinâmico, e o pico depois do AAC ficou em -1,2 dBTP, fora do alvo.
3. **Detalhes que o prompt não definia:** a música entra com fade-in de 1 s, junto com o vídeo; o fade-out de vídeo dura 2,5 s, como o da música; e o corte cai 2 quadros antes de cada frase.

## Pontos fracos que ficaram

### Falta de imagem para o que a narração diz
- **Frase 13 (FBI, 1979):** repete o bote do C03 21 s depois do primeiro uso. É o ponto mais fraco do vídeo.
- **Frase 7 (Allen West):** não tem imagem própria e fica sob as capas de chuva.
- **Frase 14 e final:** repetem o C07 como fechamento simétrico com a abertura. É defensável, mas é repetição.

### Trechos esticados ou acelerados
- **Trecho 4 (C04):** 0,67x mais 1,58 s de quadro congelado. O clipe só tem 1,8 s utilizáveis entre o flash inicial da imagem pronta (quadros 0 a 20) e a etiqueta "Prak odanline" (quadro 66 em diante).
- **Trecho 6 (C10):** 7 s a 0,67x, bem mais lento que o resto.
- **Trecho 12 (C07):** 0,70x.
- **Trecho 8 (C01):** 1,32x, no limite.

### Erros de texto e de conteúdo que continuam visíveis
- **C08, de 7,6 a 10,8 s, em destaque:** o calendário diz "JUNE" em inglês, tem junho com dia 31, pula o dia 8 e mostra "223". O carimbo "23 JUN 13" não faz sentido.
- **C09, de 42,4 a 50,4 s:** são **16 riscos** para a etiqueta "14 TENTATIVAS", e o carimbo "NELDEN ERA 17.2.92" não faz sentido.
- **C04:** carimbo "ALFOTFC" e jornal "FRU…" nas bordas. São pequenos.
- **C07, depois do remendo:** as duas tiras em inglês sumiram. Sobram dois resíduos:
  - Por cerca de 0,17 s o texto de baixo aparece parcialmente sob o carimbo em movimento, antes do remendo entrar. Isso acontece por volta de 3,8–4,0 s e de 60,5–60,7 s.
  - Com o vídeo pausado, dá para notar uma leve diferença de textura no remendo de baixo.
- **C01:** o colete desenhado é social, não salva-vidas, e o fundo é um campo, não a baía.
- **C02:** furadeira elétrica moderna; a broca real foi improvisada com motor de aspirador.
- **C07 e C09:** a ilha é genérica, com farol e casinha, e não tem a silhueta de Alcatraz. Só o C03 mostra a silhueta correta.
- **Ficaram de fora por corte:** os jornais falsos de C05 e C10 e as etiquetas "Prak odanline", "Deasbolt" e "ALGOOT LISE" de C04.

### Áudio
- O limitador corta até 5,8 dB nos picos da voz. Isso pode achatar um pouco as plosivas. Avaliei só por medição; não ouvi o resultado.
- A trilha já vem com clipping no arquivo original.
- A narração foi gerada em 24 kHz, então não tem conteúdo acima de 12 kHz, e converter para 48 kHz não recupera isso.
- Não avaliei o caráter musical da trilha, porque não consigo ouvi-la. Pelo título, "Honor and Sword", ela pode ser épica demais para o tom de mistério.

### Licença da trilha (Pixabay)
A licença do Pixabay permite uso comercial e não exige atribuição. O risco que sobra é uma reivindicação de Content ID no YouTube, caso o artista tenha registrado a faixa. Não verifiquei se esta faixa está registrada. Guarde o link da página e a data do download para contestar, se aparecer reivindicação.

## Clipes novos que valem a pena, em ordem de prioridade
Em todos, peça "nenhum texto legível". O gerador errou texto em 7 dos 10 clipes.

1. **Frase 13 (6,4 s):** pasta de arquivo de papel kraft sendo fechada e amarrada com barbante vermelho, carimbo vermelho sem letras e três silhuetas recortadas dentro.
2. **Frase 7 (3,5 s):** quadro de cortiça com quatro fotos tarjadas; a quarta fica para trás, presa atrás de uma grade de ventilação parafusada. Com esse clipe, as capas (C10) ficam só com a frase 6, de 25,04 a 28,50 s, quase em 1x.
3. **Substituir o C08:** o mesmo guarda, sem calendário.
4. **Substituir o C01:** colete salva-vidas de cortiça, laranja desbotado, sobre areia molhada.

Para trocar um clipe: adicione o arquivo em `CLIPS`, ajuste a linha correspondente em `PLAN` e rode o script de novo. Ele recalcula velocidade e congelamento e avisa se algum limite for violado.
