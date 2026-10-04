# Lições aprendidas

Cada item abaixo aconteceu de verdade num projeto e custou retrabalho. Leia antes de montar o plano de corte.

## Clipes

**1. Flash da imagem de referência.** Clipes image-to-video (Veo e outros) começam com a imagem de entrada pronta e depois "piscam" para o início da animação. Num projeto de 10 clipes, todos tinham isso: 2 quadros na maioria, 7 num clipe, cerca de 20 em dois deles. Se o corte começar no quadro 0, o espectador vê a cena final por um instante, depois tudo some e se remonta.
→ O `analisar` detecta o flash pela queda de densidade de bordas e informa `inicio_seguro_quadro`, e o `plano` avisa quando um corte começa antes dele. Mesmo assim, confira na grade: a detecção é heurística.

**2. Número de quadro errado nas grades.** Uma grade feita com `select` e rótulo `%{n}` desenhado **depois** do `select` numera os quadros selecionados (0, 1, 2…), não os de origem. Isso levou a escolher o quadro 8 achando que era "depois do flash", quando o flash ia até o 20.
→ Desenhe o rótulo **antes** do `select`. As grades do `analisar` já fazem assim (`q48` = quadro 48 do clipe).

**3. Texto ruim é a regra, não a exceção.** Erros encontrados em 7 de 10 clipes:
- frases sem sentido em inglês numa narração em português;
- calendário com "JUNE", junho com dia 31, dia 8 faltando e "223";
- 16 riscos de contagem para uma etiqueta "14 TENTATIVAS";
- carimbos e jornais ilegíveis.

→ Cortar o trecho resolve parte. Às vezes dá para cortar logo antes de a etiqueta errada aparecer e congelar 1 a 2 s, sem passar dos limites. Remendo resolve tira de texto sobre fundo liso. O resto vai para o relatório com o tempo exato, junto com a sugestão de gerar o clipe de novo pedindo "nenhum texto legível".

**4. Palavra ambígua no prompt de geração vira objeto errado.** "Colete salva-vidas" virou colete social; "broca improvisada" virou furadeira elétrica moderna.
→ Na hora de sugerir clipes novos, descreva o objeto sem ambiguidade (material, cor, formato) e, se preciso, em inglês.

**5. Cobertura.** A soma dos clipes pode passar da duração da narração (80 s de clipe para 61 s de fala) e mesmo assim faltar imagem para 3 de 14 frases. Duração não é cobertura.
→ Mapeie frase por frase. Para cada frase sem imagem, decida entre reaproveitar outro clipe, juntar com a frase vizinha ou pedir um clipe novo, e mostre isso no plano.

**6. Um clipe pode servir a duas frases, mas repetir um clipe aparece.** Repetir o mesmo plano 20 s depois é o ponto mais fraco de um vídeo curto. A exceção defensável é abrir e fechar com o mesmo plano, como moldura.

## Remendos

**7. Contorno fantasma.** Um remendo do tamanho exato da tira deixa aparecer a borda e a sombra dela, porque a borda suave mistura o original de volta.
→ Cubra tira e sombra com folga maior que `borda`. Confira com um recorte antes/depois.

**8. Objeto passando por cima.** Um carimbo atravessava a área do remendo por cerca de 1 s. O remendo "apagaria" o carimbo.
→ Use `desde`/`ate` (quadros de origem) para o remendo só valer com a área livre. Avise no relatório se o texto aparece por alguns quadros antes do remendo entrar.

**9. Borda seca alinhada.** Quando o remendo encosta em algo (uma fita adesiva, por exemplo), borda suave cria degradê no objeto.
→ Use `borda_inferior: false` com a borda exatamente no topo do objeto.

## Áudio

**10. Mono contra estéreo.** Narração mono medida contra música estéreo erra a diferença de nível em cerca de 3 dB. Ao mixar, a voz vira estéreo dual-mono e ganha cerca de 3 dB.
→ O script mede as duas em estéreo.

**11. "10–12 dB abaixo da voz" e ducking somam.** Com limiar 0,02 e ratio 8, o ducking sozinho tira de 9 a 15 dB. Ajustar a trilha 11 dB abaixo **antes** do ducking deixou a música 20 dB abaixo durante a fala, ou seja, inaudível no celular.
→ Calibre o nível **depois** do ducking. O script faz isso: o ganho do ducking depende só da chave, então o nível da trilha muda 1:1 com o ganho.

**12. Bombeamento com a narração crua como chave.** Medido: a música ficava cerca de 20 dB abaixo nas palavras e subia de 12 a 17 dB em cada pausa de 0,5 a 1 s. Somar cópias atrasadas da voz como "hold" não resolveu, porque ainda subia de 4 a 13 dB: o fim das frases é baixo demais.
→ A chave virou o envelope fala/pausa (pausas menores que 1,2 s preenchidas) com nível fixo. Com isso a variação ficou entre -2 e +2 dB, que é a dinâmica da própria música. Os parâmetros do compressor continuam os pedidos.

**13. `loudnorm` em modo dinâmico.** Com a voz de TTS (fator de crista de cerca de 19 dB) indo para -14 LUFS, o `loudnorm` de duas passagens caiu no modo dinâmico. Além disso, o AAC levou o pico de -1,5 para -1,2 dBTP.
→ Ganho fixo mais `alimiter` a 4x de taxa (aproxima o pico real) com teto de -2,3 dB, medindo o pico **no AAC** e baixando o teto se precisar. Relate quanto o limitador trabalha (no primeiro projeto: 24% do tempo, média de 2,3 dB, máximo de 5,8 dB).

**14. Trilha de biblioteca.** Pode vir com silêncio no início (2 a 3 s) e com clipping (+0,2 dBTP).
→ Comece onde ela tem corpo e relate o clipping de origem.

**15. Transcrição sem tempo por palavra.** O `creative_transcribe_audio` do ElevenLabs via MCP devolve só o texto.
→ Use o `alinhar` com as pausas. No primeiro projeto ele acertou as 14 fronteiras de frase. Se o usuário tiver o roteiro, use o roteiro e não gaste créditos.

## Processo

**16. Revise a folha de revisão antes de entregar.** O primeiro render tinha três cortes começando dentro do flash ou com jornal falso na tela. Só a folha com o primeiro, o do meio e o último quadro de cada trecho mostrou isso.

**17. Você não ouve o áudio.** Toda avaliação de áudio é por medição. Diga isso ao usuário em vez de afirmar que "soa bem".
