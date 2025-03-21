JEKYLL_VERSION=4.4

.PHONY: serve update build help docker-build

serve:
	docker run --rm \
		-v ${PWD}:/srv/jekyll \
		-u $(id -u):$(id -g) \
		-p 4000:4000 \
		jekyll serve --host 0.0.0.0

update:
	rm Gemfile.lock
	docker run --rm \
		-v ${PWD}:/srv/jekyll \
		-u $(id -u):$(id -g) \
		jekyll

build:
	docker run --rm \
		-v ${PWD}:/srv/jekyll \
		-u $(id -u):$(id -g) \
		jekyll build

trace:
	docker run --rm \
		-v ${PWD}:/srv/jekyll \
		-u $(id -u):$(id -g) \
		jekyll build --trace

docker-build:
	docker build -t jekyll .

help:
	@echo "Available commands:"
	@echo "  make serve        - Start the Jekyll development server"
	@echo "  make update      - Update Ruby dependencies"
	@echo "  make build       - Build the Jekyll site"
	@echo "  make docker-build - Build the Jekyll Docker image"
	@echo "  make help        - Show this help message" 