# Pokopia — ícones de botão para Steam Deck, Xbox e PlayStation

Mod para **Pokémon Pokopia** (Switch 2, versão **2.0.1 / 2.0.1a**, update `655360`) em emuladores da família
yuzu/Eden/Eglantine. Ele troca os ícones de botão do jogo (A, B, X, Y, L, R, ZL, ZR, +, −, clique nos sticks)
pelos do controle que você usa, para o jogo mostrar **o botão que você realmente aperta**.

Este repositório **não contém nenhum arquivo do jogo**. O script lê o **seu** jogo e gera o mod localmente.

## Por que os botões ficam trocados

O emulador mapeia o controle **por posição**: o botão da direita do seu controle é o A do Switch, o de baixo é
o B, e assim por diante. Só que as letras mudam de lugar entre os consoles:

| Posição | Switch | Steam Deck | Xbox | PlayStation |
|---|---|---|---|---|
| Direita | A | **B** | **B** | **○** |
| Embaixo | B | **A** | **A** | **✕** |
| Em cima | X | **Y** | **Y** | **△** |
| Esquerda | Y | **X** | **X** | **□** |
| Ombros | L / R | **L1 / R1** | **LB / RB** | **L1 / R1** |
| Gatilhos | ZL / ZR | **L2 / R2** | **LT / RT** | **L2 / R2** |
| Meio | + / − | **☰ / ⧉** | **☰ / ⧉** | **Options ☰ / Create** |
| Clique nos sticks | L / R | **L3 / R3** | **LS / RS** | **L3 / R3** |

O mod troca:

- o **atlas de ícones do HUD e das dicas** (`bc2c37f5`, textura 18 — 1024×1024);
- o botão desenhado na **tela de título** (`79c6dd0e`, "PRESS Ⓐ BUTTON" / "APERTE O BOTÃO Ⓐ").

## Requisitos

- Python 3.10+ com `pillow` e `numpy` (`pip install pillow numpy`)
- o romfs do Pokopia 2.0.1 (a pasta que contém `motor_asset_re/` e `LD_C0_R.BIN`)
- uma fonte TrueType em negrito (o script procura Noto Sans Bold / DejaVu Sans Bold / Arial Bold; ou use `--font`)

## Como gerar

```bash
# só os botões
python3 tools/build_mod.py --game "/caminho/do/romfs" --variant steamdeck --out build/

# os três controles de uma vez
python3 tools/build_mod.py --game "/caminho/do/romfs" --variant all --out build/

# junto com a tradução PT-BR (os dois mexem nos mesmos arquivos, então precisam ser combinados)
python3 tools/build_mod.py --game "/caminho/do/romfs" --variant steamdeck \
    --base "/caminho/do/mod/Traducao PT-BR v2.5.0" --out build/
```

Cada variante vira uma pasta, por exemplo `build/Botoes Steam Deck/romfs/...`.

### Modo "no lugar" (recomendado para distribuir): funciona com ou sem a tradução

```bash
python3 tools/build_mod.py --game "/caminho/do/romfs" --variant all --inplace --out build/
```

Em vez de relocar o atlas pelo `root.rdb`, regrava os ícones **no mesmo lugar** dentro do pacote da interface
(`0x00011c54.fdata`). A versão editada, comprimida, cabe no espaço da original; o resto é completado com zeros,
os 8 bytes de cada bloco são mantidos e o 1º parâmetro (CRC32 dos dados gravados) é atualizado. Como não mexe no
`root.rdb`, pode ficar ativo **junto com o mod PT-BR**. A pasta gerada fica com ~140 MB (o pacote inteiro).

Limitação: com a tradução PT-BR ativa, a tela de título usa a imagem da tradução e continua com o Ⓐ.

O mod PT-BR usado como base é o [pokemon-pokopia-pt-br](https://github.com/LucianoNeo/pokemon-pokopia-pt-br),
de LucianoNeo (v2.5.0). O script lê a tradução da pasta que você indicar; nada dela é distribuído aqui.

## Como instalar

Copie a pasta gerada para a pasta de mods do jogo no emulador:

```
<pasta de dados do emulador>/load/0400A3A01EE4C000/<nome da pasta gerada>/romfs/...
```

No Eden/Eglantine em Linux, a pasta de dados é `~/.local/share/eden/`.

- Ative **só uma** variante por vez.
- Se for usar com a tradução PT-BR, gere com `--base` e **desative o mod PT-BR separado**
  (os dois substituem o `root.rdb`, e o emulador só aplica um deles).
- A tradução PT-BR pede o idioma do jogo em **inglês**.

## Como funciona (técnico)

O Pokopia usa o sistema de arquivos KIDS da Koei Tecmo:

- `root.rdb` (`_DRK0000`): um registro `IDRK0000` por arquivo; os últimos 13 bytes são a localização
  (`01 04`, u32 posição, u32 tamanho do registro, u16 índice do pacote no `root.rdx`); a flag `0x400000`
  marca dados comprimidos.
- `*.fdata` (`PDRK0000`): registros `IDRK0000` em sequência, com dados zlib em blocos de 16 KB
  (cada bloco: u16 tamanho, 8 bytes, zlib). O 1º parâmetro do registro é o CRC32 dos dados.
- Texturas `.g1t` (`GT1G0600`, plataforma `0x18`): BC1/BC3/BC4/BC5/BC7 em block-linear da Tegra, com o
  tiling nativo do Switch 2 (os bits 5 e 6 do endereço trocados, como o `NativeGobOffset` do Eglantine).

O script decodifica o atlas, redesenha os ícones, recodifica em BC3 (mesmo tamanho por bloco do BC7 original),
anexa o `.g1t` novo, sem compressão, ao fim do `0x4b13d561.fdata` e redireciona o registro no `root.rdb`.
Essa é a mesma técnica que o mod PT-BR usa para as imagens traduzidas.

Ferramentas em `tools/`:

| Arquivo | Para quê |
|---|---|
| `kt_scan.py` | lista e extrai os registros de um `.fdata` |
| `kt_rdb.py` | lê o `root.rdb` e compara dois índices |
| `g1t_decode.py` | decodifica e recodifica texturas `.g1t` do Switch 2 |
| `glyphs.py` | desenha os ícones de cada plataforma |
| `build_mod.py` | gera o mod |

## Limitações

- Feito e testado na versão 2.0.1a com o Eglantine (build 177) no Steam Deck.
- Pressupõe o controle mapeado **por posição** no emulador, que é o padrão.
- Imagens com o botão desenhado dentro de outras telas, se houver, não foram trocadas. Abra uma issue
  com um print.
