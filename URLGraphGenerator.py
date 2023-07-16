import jinja2


class URLGraphGenerator:
    def __init__(self, template_path):
        self.template_path = template_path
        template_loader = jinja2.FileSystemLoader(searchpath="./templates")
        template_env = jinja2.Environment(loader=template_loader)
        self.template = template_env.get_template("report_template.html")

    def generate_graph(self, url_sequences, output_path):
        html_output = self.template.render(url_sequences=url_sequences)
        with open(output_path, "w") as f:
            f.write(html_output)
