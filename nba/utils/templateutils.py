from string import Template


class TemplateUtils:
    @staticmethod
    def format(file, terms_dict):
        with open(file, 'r') as f:
            src = Template(f.read())
            return src.substitute(terms_dict)
