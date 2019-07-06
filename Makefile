ALL: up
build:
	docker-compose -f docker-compose.yml build
up:
	docker-compose -f docker-compose.yml up -t 3
stop:
	docker-compose stop
