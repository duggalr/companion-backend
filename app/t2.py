import os

fp = '/opt/elasticbeanstalk/deployment/env'
li = open(fp).readlines()
for line in li:
    k, v = line.split('=')[0], line.split('=')[1]
    os.environ[k] = v

for val in os.environ:
    print(val)

print(os.environ['REDIS_URL'])
