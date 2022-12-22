export PROJECTNAME=$(shell basename "$(PWD)")

.SILENT: ;               # no need for @

setup: ## Setup Virtual Env
	python3.10 -m venv venv
	./venv/bin/pip3 install -r requirements/dev.txt
	./venv/bin/python3 -m pip install --upgrade pip

deps: ## Install dependencies
	./venv/bin/pip3 install -r requirements/dev.txt
	./venv/bin/pip3 install -r requirements/ui.txt

clean: ## Clean package
	find . -type d -name '__pycache__' | xargs rm -rf
	rm -rf build dist

pre-commit: ## Manually run all precommit hooks
	./venv/bin/pre-commit install
	./venv/bin/pre-commit run --all-files

pre-commit-tool: ## Manually run a single pre-commit hook
	./venv/bin/pre-commit run $(TOOL) --all-files

build: clean pre-commit ## Build package
	echo "✅ Done"

deploy: clean ## Copies any changed file to the server
	ssh ${PROJECTNAME} -C 'bash -l -c "mkdir -vp ./${PROJECTNAME}"'
	rsync -avzr \
		.env \
		common_utils.py \
		twitter_api.py \
		yt_api.py \
		requirements \
		rider_brain_bot.py \
		webpage_to_pdf.py \
		Readability.js \
		hn_new_github_repos.py \
		scripts \
		${PROJECTNAME}:./${PROJECTNAME}

start: deploy ## Sets up a screen session on the server and start the app
	ssh ${PROJECTNAME} -C 'bash -l -c "./${PROJECTNAME}/scripts/setup_jobs.sh"'

stop: deploy ## Stop any running screen session on the server
	ssh ${PROJECTNAME} -C 'bash -l -c "./${PROJECTNAME}/scripts/stop_jobs.sh"'

ssh: ## SSH into the target VM
	ssh ${PROJECTNAME}

syncdatabases: ## Copy databases from remote to local
	rm -rf output_dir/*.db
	rsync -avzr ${PROJECTNAME}:./hn_new_github_repos.* output_dir/
	rsync -avzr ${PROJECTNAME}:./rider_brain.* output_dir/

bpython: ## Runs bpython
	./venv/bin/bpython

.PHONY: help
.DEFAULT_GOAL := help

help: Makefile
	echo
	echo " Choose a command run in "$(PROJECTNAME)":"
	echo
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
	echo
