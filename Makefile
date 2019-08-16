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
	ps ax | grep [r]un.py
kill:
	kill $(ps ax | grep [r]un.py | awk '{print $1}')
log:
	tail -F app.log
