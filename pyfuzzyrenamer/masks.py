import re

from pyfuzzyrenamer import filters, utils


def mask_processed(file, masks, re_filters, applyFilters=True):
    stem, suffix = utils.GetFileStemAndSuffix(file)
    ret = stem
    # apply masks
    interval = set()
    for mask in masks:
        matches = mask.search(ret)
        if matches:
            for groupNum in range(0, len(matches.groups())):
                groupNum = groupNum + 1
                interval = set.union(
                    interval,
                    {*range(matches.start(groupNum), matches.end(groupNum) + 1)},
                )
    interval_lst = sorted(interval)
    post = ""
    pre = ""
    middle = stem
    if interval_lst:
        grp = list(utils.group(interval_lst))
        if grp[0][0] == 0:
            pre = stem[grp[0][0] : grp[0][1]]
            if len(grp) > 1 and grp[-1][1] == len(stem):
                post = stem[grp[-1][0] : grp[-1][1]]
                middle = stem[grp[0][1] : grp[-1][0]]
            else:
                middle = stem[grp[0][1] :]
        elif grp[-1][1] == len(stem):
            post = stem[grp[-1][0] : grp[-1][1]]
            middle = stem[: grp[-1][0]]
    if applyFilters:
        # convert to lowercase.
        middle = middle.lower()
        # remove leading and trailing whitespaces.
        middle = middle.strip()
        # apply filters
        for re_filter in re_filters:
            middle = re_filter[0].sub(re_filter[1], middle)
        middle = " ".join(middle.split())
    return pre, middle, post


def CompileMasks(s_filters):
    ret = []
    lines = s_filters.splitlines()
    it = iter(lines)
    for l1, l2 in zip(it, it):
        if l1.startswith("+"):
            try:
                ret.append(re.compile(l2.strip()[1:-1], re.IGNORECASE))
            except re.error:
                pass
    return ret


class FileMasked:
    masks = []

    def __init__(self, file):
        self.file = file
        self.masked = mask_processed(
            file, FileMasked.masks, filters.FileFiltered.filters
        )
