.PHONY: build upload run

build:
	@docker build -f cicd/Dockerfile -t $${DOCKERHUB_USERNAME}/sentinel3-sral-demo:latest .;

upload:
	@$(MAKE) build;
	@/bin/bash -c 'set -a; source .envrc; set +a; echo "$$DOCKERHUB_PASSWORD" | docker login -u "$$DOCKERHUB_USERNAME" --password-stdin';
	@docker push $${DOCKERHUB_USERNAME}/sentinel3-sral-demo:latest;

run:
	@docker run -it -v ~/.eumdac:/root/.eumdac $${DOCKERHUB_USERNAME}/sentinel3-sral-demo:latest
