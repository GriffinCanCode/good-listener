.PHONY: install-backend install-frontend start-backend start-frontend start-all clean check-env

# Environment Variables
PYTHON := python3
NPM := npm

install-backend:
	cd backend && $(PYTHON) -m venv venv && \
	. venv/bin/activate && \
	pip install -r requirements.txt && \
	echo "Backend dependencies installed."

install-frontend:
	cd frontend && $(NPM) install && \
	echo "Frontend dependencies installed."

install: install-backend install-frontend

start-backend:
	@echo "Cleaning port 8000..."
	./scripts/kill_port.sh 8000
	@echo "Starting Backend..."
	cd backend && \
	. venv/bin/activate && \
	$(PYTHON) -m app.main

start-frontend:
	@echo "Cleaning port 5173..."
	./scripts/kill_port.sh 5173
	@echo "Starting Frontend (Vite + Electron)..."
	cd frontend && $(NPM) run electron:dev

start-all:
	@echo "Starting Full Stack..."
	make -j 2 start-backend start-frontend

clean:
	rm -rf backend/venv
	rm -rf backend/__pycache__
	rm -rf frontend/node_modules
	rm -rf frontend/build
	rm -rf frontend/dist
	echo "Cleaned project artifacts."

check-env:
	@echo "Checking requirements..."
	@command -v $(PYTHON) >/dev/null 2>&1 || { echo >&2 "Python is not installed."; exit 1; }
	@command -v $(NPM) >/dev/null 2>&1 || { echo >&2 "NPM is not installed."; exit 1; }
	@echo "Environment looks good."

