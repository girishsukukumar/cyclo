import json

json_string = '{"first_name":"Girish", "last_name": "Kumar"}'

parsed_json = json.loads(json_string)
print parsed_json
print(parsed_json['first_name'])
