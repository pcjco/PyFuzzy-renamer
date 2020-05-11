import re

from pyfuzzyrenamer import utils


def filter_processed(file, re_filters):
    stem, suffix = utils.GetFileStemAndSuffix(file)
    ret = stem
    # convert to lowercase.
    ret = ret.lower()
    # remove leading and trailing whitespaces.
    ret = ret.strip()
    # apply filters
    for re_filter in re_filters:
        try:
            ret = re_filter[0].sub(re_filter[1], ret)
        except re.error:
            pass
    ret = " ".join(ret.split())
    return ret


def CompileFilters(filters):
    ret = []
    lines = filters.splitlines()
    it = iter(lines)
    for l1, l2, l3 in zip(it, it, it):
        if l1.startswith("+"):
            try:
                ret.append((re.compile(l2.strip()[1:-1]), l3.strip()[1:-1], re.IGNORECASE))
            except re.error:
                pass
    return ret


class FileFiltered:
    filters = []

    def __init__(self, file):
        self.file = file
        self.filtered = filter_processed(file, FileFiltered.filters)
