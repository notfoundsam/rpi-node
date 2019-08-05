ALL: up
build:
	docker-compose -f docker-compose.yml build
up:
	nohup python3 run.py > output.log &
up-dev:
	docker-compose -f docker-compose.yml up -t 3
stop:
	docker-compose stop
ps:
	ps ax | grep run.py
