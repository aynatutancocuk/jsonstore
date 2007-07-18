from pkg_resources import iter_entry_points


def EntryManager(dsn):
    """
    Generic entry manager.

    This class delegates a connection to the proper manager.
    
    """
    protocol, location = dsn.split('://', 1)

    # Check available backends.
    for entrypoint in iter_entry_points("jsonstore.backend"):
        if entrypoint.name == protocol:
            em = entrypoint.load()
            return em(location)

    raise Exception('No backend found for protocol "%s"!' % protocol)
