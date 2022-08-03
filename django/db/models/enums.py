import enum
from types import DynamicClassAttribute

from django.utils.functional import Promise

__all__ = ["Choices", "IntegerChoices", "TextChoices"]


class ChoicesMeta(enum.EnumMeta):
    """A metaclass for creating a enum choices."""

    def __new__(metacls, classname, bases, classdict, **kwds):
        labels = []
        named_groups = []
        key_order = []
        for key in list(classdict._member_names):
            value = classdict[key]
            # Check if value is a named group
            if hasattr(value, "choices"):
                named_group = value.__label__ if hasattr(value, "__label__") else key
                for member in value:
                    key_order.append(member.name)
                    classdict[member.name] = member
                    labels.append(member.label)
                    named_groups.append(named_group)
                continue
            if (
                isinstance(value, (list, tuple))
                and len(value) > 1
                and isinstance(value[-1], (Promise, str))
            ):
                *value, label = value
                value = tuple(value)
            else:
                label = key.replace("_", " ").title()
            key_order.append(key)
            labels.append(label)
            named_groups.append(None)
            # Use dict.__setitem__() to suppress defenses against double
            # assignment in enum's classdict.
            dict.__setitem__(classdict, key, value)
        classdict._member_names.clear()
        classdict._member_names.extend(key_order)
        cls = super().__new__(metacls, classname, bases, classdict, **kwds)
        values = (cls.__members__[x] for x in key_order)
        for member, label, named_group in zip(values, labels, named_groups):
            member._label_ = label
            member._named_group_ = named_group
        return enum.unique(cls)

    def __contains__(cls, member):
        if not isinstance(member, enum.Enum):
            # Allow non-enums to match against member values.
            return any(x.value == member for x in cls)
        return super().__contains__(member)

    @property
    def names(cls):
        empty = ["__empty__"] if hasattr(cls, "__empty__") else []
        return empty + [member.name for member in cls]

    @property
    def choices(cls):
        choices = []
        choice_list = choices
        last_named_group = None
        for member in cls:
            if member.named_group != last_named_group:
                last_named_group = member.named_group
                if member.named_group:
                    choice_list = []
                    choices.append((member.named_group, choice_list))
                else:
                    choice_list = choices  # Add to toplevel
            choice_list.append((member.value, member.label))
        empty = [(None, cls.__empty__)] if hasattr(cls, "__empty__") else []
        return empty + choices

    @property
    def flatchoices(cls):
        """Flattened version of choices tuple."""
        empty = [(None, cls.__empty__)] if hasattr(cls, "__empty__") else []
        return empty + [(member.value, member.label) for member in cls]

    @property
    def labels(cls):
        return [label for _, label in cls.flatchoices]

    @property
    def values(cls):
        return [value for value, _ in cls.flatchoices]


class Choices(enum.Enum, metaclass=ChoicesMeta):
    """Class for creating enumerated choices."""

    @DynamicClassAttribute
    def label(self):
        return self._label_

    @DynamicClassAttribute
    def named_group(self):
        return self._named_group_

    @property
    def do_not_call_in_templates(self):
        return True

    def __str__(self):
        """
        Use value when cast to str, so that Choices set as model instance
        attributes are rendered as expected in templates and similar contexts.
        """
        return str(self.value)

    # A similar format was proposed for Python 3.10.
    def __repr__(self):
        return f"{self.__class__.__qualname__}.{self._name_}"


class IntegerChoices(int, Choices):
    """Class for creating enumerated integer choices."""

    pass


class TextChoices(str, Choices):
    """Class for creating enumerated string choices."""

    def _generate_next_value_(name, start, count, last_values):
        return name
