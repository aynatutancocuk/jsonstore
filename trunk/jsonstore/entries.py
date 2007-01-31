"""
A simple EntryManager.

Entries are stored as dicts, using for keys the integers
as strings ("1", "2", "3", etc.) as default.

"""
import time
import operator
import re

from shove import Shove


class EntryManager(object):
    def __init__(self, location, **kwargs):
        self.store = Shove(location, **kwargs)
    
    def create_entry(self, entry):
        """
        Create an entry in the entry manager::

            >>> entry = {}
            >>> entry['content'] = {'content': "<p>This is an entry.</p>"}
            >>> entry['author'] = {'name': "Roberto De Almeida",
            ...                    'email': "roberto@dealmeida.net"}
            >>> em.create_entry(entry)

        If empty, 'id' and 'updated' will be automatically set.

        """
        # Required elements.
        entry.setdefault('id', self._next_id())
        entry.setdefault('updated', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()))

        # Store entry.
        self.store[str(entry["id"])] = entry
        return entry

    def get_entry(self, key):
        """
        Retrieve an entry by its id::
        
            >>> entry = em.get_entry("1")

        Will return a dict describing the entry.

        """
        entry = self.store[str(key)]
        return entry

    def get_entries(self, size=None, offset=0):
        """
        Retrieve last n entries, sorted by the 'updated' attribute and in
        descending order::

            >>> entries = em.get_entries(10)

        If you omit the number, all entries will be retrieved.

        You can also specify an offset::

            >>> entries = em.get_entries(10, 5)

        This will skip the first 5 entries.

        """
        entries = self.store.values()

        # Sort by time.
        entries.sort(key=operator.itemgetter('updated'), reverse=True)
        if size is not None: size += offset
        entries = entries[offset:size]
        return entries

    def delete_entry(self, key):
        """
        Delete an entry identified by its key::

            >>> em.delete_entry("1")

        """
        del self.store[str(key)]

    def update_entry(self, new_entry):
        """
        Update an entry.
        
            >>> entry = {'title': "This is an entry"}
            >>> entry = em.create_entry(entry)
            >>> print entry['id']
            0
            >>> entry['title'] = "A different title"
            >>> em.update_entry(entry)

        """
        # Retrieve old entry and update id.
        entry = self.store[str(new_entry["id"])]
        entry.update(new_entry)

        # Update 'updated'.
        entry['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
        
        # Store it back.
        self.store[str(entry["id"])] = entry
        return entry

    def search(self, filters, flags=0):
        """
        Search all entries.

        A simple, case-sensitive search for the word "Python" in the title::

            >>> entries = em.search({"title": "Python"})

        For case-insensitive searching in the content::

            >>> entries = em.search({"content": {"content": "Python"}}, re.IGNORECASE)

        """
        def filter_(entry, filters, flags=0):
            # If entry is a list, only a single value needs to match.
            if isinstance(entry, list):
                for item in entry:
                    if filter_(item, filters, flags): return True
                return False

            # Otherwise, all filters should match the object.
            for k, v in filters.items():
                if isinstance(v, dict): 
                    if not filter_(entry.get(k, {}), v, flags): return False
                else:
                    # if the filter has multiple values, only one has to match.
                    if not isinstance(v, list): v = [v]
                    for m in v:
                        if re.match(m, entry.get(k, ''), flags): break
                    else:
                        return False
            return True

        entries = self.get_entries()
        entries = [entry for entry in entries if filter_(entry, filters, flags)]
        return entries

    def _next_id(self):
        # List keys.
        keys = self.store.keys()
        keys = [key for key in keys if re.match(r"^\d+$", key)]
        keys.sort(key=int)
        
        # Get a new key.
        key = keys and str(int(keys[-1]) + 1) or "0"
        return key

    def close(self):
        self.store.close()
