.PHONY: help install run run-full test lint clean

help:
	@echo "Comandos disponibles:"
	@echo "  make install      Instala dependencias"
	@echo "  make run          Ejecuta el collector (demo + manual)"
	@echo "  make run-full     Ejecuta con todas las fuentes disponibles"
	@echo "  make test         Corre los tests"
	@echo "  make lint         Revisa estilo (requiere ruff)"
	@echo "  make serve        Levanta servidor HTTP local para el dashboard"
	@echo "  make clean        Elimina archivos temporales"

install:
	pip install -r requirements.txt

run:
	python collector.py --zona "Guadalajara Centro" --precio-max 20000 --sources demo manual

run-full:
	python collector.py --zona "Guadalajara Centro" --precio-max 20000

run-verbose:
	python collector.py --zona "Guadalajara Centro" --precio-max 20000 --sources demo manual -v

test:
	python -m pytest tests/ -v

test-quick:
	python -m pytest tests/ -q

lint:
	@command -v ruff >/dev/null 2>&1 && ruff check src/ tests/ collector.py || echo "ruff no instalado; ejecuta: pip install ruff"

serve:
	@echo "Dashboard en: http://localhost:8000/rental-monitor-gdl/dashboard.html"
	cd .. && python -m http.server 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
