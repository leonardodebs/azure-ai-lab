"""Configuração compartilhada de testes.

Coloca a raiz do projeto e `src/` no sys.path para importar os módulos como
`import compare_models`, etc. Os testes exercitam apenas a lógica determinística
que NÃO depende de credenciais Azure/AWS/GCP — os imports de nuvem ficam dentro
das funções, então importar os módulos é seguro e não faz chamadas reais.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
SCRIPTS = ROOT / "scripts"
for caminho in (str(ROOT), str(SRC), str(SCRIPTS)):
    if caminho not in sys.path:
        sys.path.insert(0, caminho)
