import yaml

def get_input_node(input_vars: list[str]) -> dict:
    return {
        "captureInput": {
            "set": {var: "${ $input.%s}" % var for var in input_vars}
        }
    }

def get_agent_node(input_var_name: str, agent_name: str) -> dict:
    task_name = "run%s" % agent_name
    return {
        task_name: {
            "call": "activity",
            "with": {
                "name": "activity.execute_agent",
                "arguments": [
                    "${ $data.%s }" % input_var_name,
                    agent_name
                ],
                "taskQueue": "activity_queue"
            }
        }
    }

def save_output(task_name: str, key: str) -> dict:
    return {
        task_name: {
            "set": {
                key: "${ $output }"
            }
        }
    }

def save_from_output(task_name: str, key: str, output_key: str) -> dict:
    return {
        task_name: {
            "set": {
                key: "$ { $output.%s}" % output_key
            }
        }
    }

def run_agent_as_subflow(input_var_name: str, agent_name: str) -> dict:
    return {
        "run%s" % agent_name: {
            "do": get_agent_node(input_var_name, agent_name)
        }
    }

def get_branch_node(reason: str, branch: dict, default: str) -> dict:
    switch = [{k: {"when": v["condition"], "then": v["task"]}} for k,v in branch.items()]
    if default:
        switch.append({
            "default": {
                "then": default
            }
        })
    task_name ="routeBy%s" % reason
    return {
        task_name: {
            "switch": switch
        }
    }

def get_default_node(task_name: str, value: str) -> dict:
    return {
        "run%s" % task_name: {
            "do": [
                {
                    "setDefault": {
                        "set": {
                            "response": value
                        }
                    }
                }
            ]
        }
    }

def get_dsl_metadata() -> dict:
    return {
        "document": {
            "dsl": "1.0.0",
            "namespace": "zigflow",
            "name": "agent-router",
            "version": "1.0.0",
        },
        "do": []
    }

if __name__ == "__main__":
    workflow = get_dsl_metadata()
    input = get_input_node(["user_query"])
    agent_node1 = get_agent_node("user_query", "intent")
    save_agent_node1_output = save_output("saveIntent", "intentResult")
    branch = get_branch_node("intent", {"hotel": {"condition": "${ $data.intentResult.type == \"HOTEL\"}", "task": "runHotel"},
                                        "restaurant": {"condition": "${ $data.intentResult.type == \"RESTAURANT\"}", "task": "runRestaurant"}}, "setDefaultMessage")
    subtask_agent_2 = run_agent_as_subflow("user_query", "hotel")
    save_output_node2 = save_from_output("saveHotelResult", "response","text")

    subtask_agent_3 = run_agent_as_subflow("user_query", "restaurant")
    save_output_node3 = save_from_output("saveHotelResult", "response","text")

    default_node = get_default_node("setDefaultMessage", "I'm not able to answer your query please try another")
    workflow["do"] = [input, agent_node1, save_agent_node1_output, branch, subtask_agent_2, save_output_node2, subtask_agent_3, save_output_node3, default_node]
    yaml_string = yaml.dump(workflow, default_flow_style=False, sort_keys=False)
    print(yaml_string)

