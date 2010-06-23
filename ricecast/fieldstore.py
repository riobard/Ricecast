
class FieldStore(object):
    ''' case-insensitive, ordered dict '''

    def __init__(self):
        self.list   = []
        self.dict   = {}

    def __setitem__(self, name, value):
        name    = name.strip().lower()
        self.list.append((name, value))
        value   = value.strip()
        self.dict[name] = value

    def get(self, name, fallback=None):
        try:
            return self.dict[name.lower()]
        except KeyError:
            return fallback

    def __getitem__(self, name):
        return self.get(name)

    def __iter__(self):
        return self.list

    def __contains__(self, name):
        return name.lower() in self.dict

    def __str__(self):
        return '\r\n'.join('%s: %s' % (name, value)
                for (name, value) in self.list)

    def __repr__(self):
        return repr(self.list)



