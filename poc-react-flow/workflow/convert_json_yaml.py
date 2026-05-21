import json

import yaml

json_file = "agent-router-workflow.json"
yaml_file = "agent-router-workflow2.yaml"

with open(json_file, 'r') as f:
    json_data = json.load(f)

    with open(yaml_file, 'w') as fy:
        yaml.dump(json_data, fy, default_flow_style=False, sort_keys=False)