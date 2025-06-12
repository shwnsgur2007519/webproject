from django import template
register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter(name='dict_get')
def dict_get(d, key):
    try:
        return d.get(key)
    except (AttributeError, KeyError, TypeError):
        return None