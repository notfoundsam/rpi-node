# Service to connect to SmartRemote

## Installation

Clone this repository into your paspberry pi
```bash
$ git clone https://github.com/notfoundsam/rpi-node.git
$ cd rpi-node
```

## Production

### Install python requirements
`$ pip install --no-cache-dir -r requirements.txt`

### Run the application
`$ python3 run.py`

### Or run it in background
`$ nohup python3 run.py > output.log &`

## Development

### Run the development mode on docker
`$ make up` or `$ docker-compose up`

### generate requirements
`$ pip freeze > requirements.txt`

### find running process
`$ ps ax | grep run.py`
