import urllib.request
import datetime
import re
import warnings
import os


__all__ = ['make_url', 'emitents']


ICHARTSURL = 'http://www.finam.ru/cache/icharts/icharts.js'
ICHARTSPATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'cache/icharts.js')

FREQS = {
    1:  ['tick', 't', 'ticks'],
    2:  ['1min', 'min'],
    3:  ['5min'],
    4:  ['10min'],
    5:  ['15min'],
    6:  ['30min'],
    7:  ['hour', 'h', 'hours', '60min'],
    8:  ['day', 'd', 'days'],
    9:  ['week', 'w', 'weeks'],
    10: ['month', 'm', 'mon', 'months'],
}

FREQS = {freqname: freqid
         for freqid, freqnames in FREQS.items()
         for freqname in freqnames}

FIELD_SEPS = {
    ',':  1,
    '.':  2,
    ';':  3,
    '\t': 4,
    ' ':  5,
}

# TODO add other separators
DIGIT_SEPS = {
    '.': 1,
}


class Emitent(object):

    def __init__(self, id, name, code, market):
        self.id = id
        self.name = name
        self.code = code
        self.market = market
        emitents.byid[self.id] = self
        emitents.bycode[self.code] = self

    def __repr__(self):
        return f'{self.name} ({self.code})'


class emitents:

    byid = {}
    bycode = {}

    @staticmethod
    def update(icharts=None):
        """Update hash tables with emitents info.

        If `icharts` is None attempts to retrieve `icharts.js` via the net.
        In case of success updates also cached version of the file.

        Args:
            icharts (bytes): icharts.js

        """
        if icharts is None:
            icharts = urllib.request.urlopen(ICHARTSURL).read()
            with open(ICHARTSPATH, 'wb') as f:
                f.write(icharts)
        variables = re.findall(r'var\s+(\S+)\s*=\s*(.+);',
                               icharts.decode('cp1251'))
        icharts = {name: eval(value) for name, value in variables}
        emitents.byid = {}
        emitents.bycode = {}
        for em in zip(icharts['aEmitentIds'], icharts['aEmitentNames'],
                      icharts['aEmitentCodes'], icharts['aEmitentMarkets']):
            Emitent(*em)


try:
    emitents.update()
except Exception as exc:
    warnings.warn(f'Failed to update emitent lists: {str(exc)}. Falling back '
                  'to a cached version.')
    with open(ICHARTSPATH, 'rb') as f:
        icharts = f.read()
    emitents.update(icharts)


def parse_date(date):
    if isinstance(date, str):
        date = datetime.datetime.strptime(date, '%Y-%m-%d')
    else:
        assert isinstance(date, datetime.datetime), (
               'dates must be either string or datetime objects')
    return date.strftime('%d.%m.%Y'), date.day, date.month - 1, date.year


def make_url(symbol, start, end=None, filename='data.csv', freq='day',
             field_sep=',', digit_sep='.', mstime=True, header=True,
             time='open'):
    """Generate URL to download stock history from Finam.

    Args:
        symbol (str): instrument symbol
        start (str, datetime): start date
        end (str, datetime): end date
        filename (str): out file name
        freq (str): candles frequency
        field_sep (str): field separator
        digit_sep (str): digits separator
        mstime (bool): use Moscow time
        header (bool): include header
        time (str): specify open or close timestamps

    Returns:
        str: url

    """
    ticker = emitents.bycode[symbol]
    # TODO make datf, mstimever, tmf, dmf tunable too
    args = {'tmf': 1, 'dmf': 1, 'mstimever': 1, 'datf': 5, 'cn': symbol,
            'code': symbol, 'market': ticker.market, 'em': ticker.id}
    if mstime: args['mstime'] = 'on'
    if header: args['at'] = 1
    if end is None: end = datetime.datetime.now()
    args['f'], args['e'] = os.path.splitext(filename)
    args['from'], args['df'], args['mf'], args['yf'] = parse_date(start)
    args['to'], args['dt'], args['mt'], args['yt'] = parse_date(end)

    try:
        args['p'] = FREQS[freq.lower()]
    except KeyError:
        raise ValueError(f'unsupported frequency "{freq}"')

    try:
        args['sep'] = FIELD_SEPS[field_sep]
    except KeyError:
        raise ValueError(f'unsupported field separator "{field_sep}"')

    try:
        args['sep2'] = DIGIT_SEPS[digit_sep]
    except KeyError:
        raise ValueError(f'unsupported digit separator "{digit_sep}"')

    if time == 'open':
        args['MSOR'] = 0
    elif time == 'close':
        args['MSOR'] = 1
    else:
        raise ValueError(f'unsupported time parameter value "{time}"')

    return f'http://export.finam.ru/{filename}?' + urllib.parse.urlencode(args)
