from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader("templates/"))
template = env.get_template("condition.yaml")
output = template.render(agent="intent", routes=[
    {"name": "hotel","condition":"${ $data.intentResult.type == \"HOTEL\" }", "run":"runHotel"},
    {"name": "restaurant", "condition": "${ $data.intentResult.type == \"RESTAURANT\" }", "run":"runRestaurant"},])
print(output)