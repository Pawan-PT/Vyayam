from django import template

register = template.Library()


@register.filter(name='friendly_phase')
def friendly_phase(value):
    """Convert internal phase names to user-friendly labels."""
    PHASE_NAMES = {
        'anatomical_adaptation_iso': 'Building Your Foundation',
        'anatomical_adaptation_ecc': 'Building Control',
        'hypertrophy': 'Building Muscle',
        'hypertrophy_plus': 'Building More Muscle',
        'strength': 'Getting Stronger',
        'deload': 'Recovery Week',
        'aa_iso': 'Building Your Foundation',
        'aa_ecc': 'Building Control',
    }
    if isinstance(value, str):
        return PHASE_NAMES.get(value, value.replace('_', ' ').title())
    return value


@register.filter(name='replace_underscores')
def replace_underscores(value):
    """Replace underscores with spaces. Usage: {{ value|replace_underscores }}"""
    if isinstance(value, str):
        return value.replace('_', ' ')
    return value


@register.filter(name='split_comma')
def split_comma(value):
    """Split a comma-separated string. Usage: {% for x in value|split_comma %}"""
    if isinstance(value, str):
        return value.split(',')
    return value


@register.filter(name='get_range')
def get_range(value):
    """{{ 5|get_range }} → range(5). Use: {% for i in exercise.sets|get_range %}"""
    try:
        return range(int(value))
    except (ValueError, TypeError):
        return range(3)
