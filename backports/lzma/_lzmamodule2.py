from cffi import FFI
import threading
import collections
import weakref

_owns = weakref.WeakKeyDictionary()

ffi = FFI()
ffi.cdef("""
#define UINT64_MAX ...
#define LZMA_CONCATENATED ...
#define LZMA_CHECK_NONE ...
#define LZMA_CHECK_CRC32 ...
#define LZMA_CHECK_CRC64 ...
#define LZMA_CHECK_SHA256 ...
#define LZMA_CHECK_ID_MAX ...
#define LZMA_DELTA_TYPE_BYTE ...
#define LZMA_TELL_ANY_CHECK ...
#define LZMA_TELL_NO_CHECK ...
#define LZMA_FILTER_LZMA1 ...
#define LZMA_FILTER_LZMA2 ...
#define LZMA_FILTER_DELTA ...
#define LZMA_FILTER_X86 ...
#define LZMA_FILTER_IA64 ...
#define LZMA_FILTER_ARM ...
#define LZMA_FILTER_ARMTHUMB ...
#define LZMA_FILTER_SPARC ...
#define LZMA_FILTER_POWERPC ...
#define LZMA_FILTERS_MAX ...
#define LZMA_STREAM_HEADER_SIZE ...
#define LZMA_MF_HC3 ...
#define LZMA_MF_HC4 ...
#define LZMA_MF_BT2 ...
#define LZMA_MF_BT3 ...
#define LZMA_MF_BT4 ...
#define LZMA_MODE_FAST ...
#define LZMA_MODE_NORMAL ...
#define LZMA_PRESET_DEFAULT ...
#define LZMA_PRESET_EXTREME ...

enum lzma_ret { LZMA_OK, LZMA_STREAM_END, LZMA_NO_CHECK,
	LZMA_UNSUPPORTED_CHECK, LZMA_GET_CHECK,
	LZMA_MEM_ERROR, LZMA_MEMLIMIT_ERROR,
	LZMA_FORMAT_ERROR, LZMA_OPTIONS_ERROR,
	LZMA_DATA_ERROR, LZMA_BUF_ERROR,
	LZMA_PROG_ERROR, ... };

enum lzma_action { LZMA_RUN, LZMA_FINISH, ...};

typedef uint64_t lzma_vli;

typedef struct {
	void* (*alloc)(void*, size_t, size_t);
	void (*free)(void*, void*);
	void* opaque;
	...;
} lzma_allocator;

typedef struct {
        const uint8_t *next_in;
        size_t avail_in;
        uint64_t total_in;

        uint8_t *next_out;
        size_t avail_out;
        uint64_t total_out;
	lzma_allocator *allocator;
	...;
} lzma_stream;

typedef struct {
	int type;
	uint32_t dist;
	...;
} lzma_options_delta;

typedef struct {
	uint32_t start_offset;
	...;
} lzma_options_bcj;

typedef struct {
	uint32_t dict_size;
	uint32_t lc;
	uint32_t lp;
	uint32_t pb;
	int mode;
	uint32_t nice_len;
	int mf;
	uint32_t depth;
	...;
} lzma_options_lzma;

typedef struct {
	lzma_vli id;
	void *options;
	...;
} lzma_filter;

bool lzma_check_is_supported(int check);

// Encoder/Decoder
int lzma_auto_decoder(lzma_stream *strm, uint64_t memlimit, uint32_t flags);
int lzma_stream_decoder(lzma_stream *strm, uint64_t memlimit, uint32_t flags);
int lzma_alone_decoder(lzma_stream *strm, uint64_t memlimit);
int lzma_easy_encoder(lzma_stream *strm, uint32_t preset, int check);

int lzma_get_check(const lzma_stream *strm);

int lzma_code(lzma_stream *strm, int action);

// Properties
int lzma_properties_size(uint32_t *size, const lzma_filter *filter);
int lzma_properties_encode(const lzma_filter *filter, uint8_t *props);
int lzma_properties_decode(lzma_filter *filter, lzma_allocator *allocator,
	const uint8_t *props, size_t props_size);
int lzma_lzma_preset(lzma_options_lzma* options, uint32_t preset);


void lzma_end(lzma_stream *strm);

// Special functions
void _pylzma_stream_init(lzma_stream *strm);
void _pylzma_allocator_init(lzma_allocator *al);
void _pylzma_allocator_init2(lzma_allocator *al, void *my_own_alloc (void*, size_t, size_t), void my_own_free (void*, void*));

void free(void* ptr);
""")

m = ffi.verify("""
#include <lzma.h>
void _pylzma_stream_init(lzma_stream *strm) {
	lzma_stream tmp = LZMA_STREAM_INIT; // macro from lzma.h
	*strm = tmp;
}

void* my_alloc(void* opaque, size_t nmemb, size_t size) { return PyMem_Malloc(size); }
void my_free(void* opaque, void *ptr) { PyMem_Free(ptr); }

void _pylzma_allocator_init(lzma_allocator *al) {
	al->alloc = *my_alloc;
	al->free = *my_free;
}
void _pylzma_allocator_init2(lzma_allocator *al, void *my_own_alloc (void*,size_t,size_t), void my_own_free (void*,void*)) {
	al->alloc = my_own_alloc;
	al->free = my_own_free;
}
""", libraries=['lzma'])

def go_and_do(f):
	def _f(x):
		return f(x)
	return _f

def _new_lzma_stream():
	ret = ffi.new('lzma_stream*')
	m._pylzma_stream_init(ret)
	return ffi.gc(ret, go_and_do(m.lzma_end))

def add_constant(c):
	globals()[c] = getattr(m, 'LZMA_' + c)

for c in ['CHECK_CRC32', 'CHECK_CRC64', 'CHECK_ID_MAX', 'CHECK_NONE', 'CHECK_SHA256', 'FILTER_ARM', 'FILTER_ARMTHUMB', 'FILTER_DELTA', 'FILTER_IA64', 'FILTER_LZMA1', 'FILTER_LZMA2', 'FILTER_POWERPC', 'FILTER_SPARC', 'FILTER_X86', 'MF_BT2', 'MF_BT3', 'MF_BT4', 'MF_HC3', 'MF_HC4', 'MODE_FAST', 'MODE_NORMAL', 'PRESET_DEFAULT', 'PRESET_EXTREME']:
	add_constant(c)

CHECK_UNKNOWN = CHECK_ID_MAX + 1
FORMAT_AUTO, FORMAT_XZ, FORMAT_ALONE, FORMAT_RAW = range(4)

BCJ_FILTERS = (m.LZMA_FILTER_X86,
	m.LZMA_FILTER_POWERPC,
	m.LZMA_FILTER_IA64,
	m.LZMA_FILTER_ARM,
	m.LZMA_FILTER_ARMTHUMB,
	m.LZMA_FILTER_SPARC)

class LZMAError(Exception):
	"""Call to liblzma failed."""

def is_check_supported(check):
	return bool(m.lzma_check_is_supported(check))

def catch_lzma_error(fun, *args):
	try:
		lzret = fun(*args)
	except:
		raise
	if lzret in (m.LZMA_OK, m.LZMA_GET_CHECK, m.LZMA_NO_CHECK, m.LZMA_STREAM_END):
		return lzret
	elif lzret == m.LZMA_DATA_ERROR:
		raise LZMAError("Corrupt...")
	else:
		raise LZMAError("Unrecognised...", lzret)

def parse_filter_spec_delta(id, dist=1):
	ret = ffi.new('lzma_options_delta*')
	ret.type = m.LZMA_DELTA_TYPE_BYTE
	ret.dist = dist
	return ret

def parse_filter_spec_bcj(id, start_offset=0):
	ret = ffi.new('lzma_options_bcj*')
	ret.start_offset = start_offset
	return ret

def parse_filter_spec_lzma(id, preset=m.LZMA_PRESET_DEFAULT, **kwargs):
	ret = ffi.new('lzma_options_lzma*')
	if m.lzma_lzma_preset(ret, preset):
		raise LZMAError("Invalid...")
	for arg, val in kwargs.items():
		if arg in ('dict_size', 'lc', 'lp', 'pb', 'nice_len', 'depth'):
			setattr(ret, arg, val)
		elif arg in ('mf', 'mode'):
			setattr(ret, arg, int(val))
		else:
			raise ValueError("Invalid...")
	return ret

def parse_filter_spec(spec):
	if not isinstance(spec, collections.Mapping):
		raise TypeError("Filter...")
	ret = ffi.new('lzma_filter*')
	try:
		ret.id = spec['id']
	except KeyError:
		raise ValueError("Filter...")
	if ret.id in (m.LZMA_FILTER_LZMA1, m.LZMA_FILTER_LZMA2):
		try:
			options = parse_filter_spec_lzma(**spec)
		except TypeError:
			raise ValueError("Invalid...")
	elif ret.id == m.LZMA_FILTER_DELTA:
		try:
			options = parse_filter_spec_delta(**spec)
		except TypeError:
			raise ValueError("Invalid...")
	elif ret.id in BCJ_FILTERS:
		try:
			options = parse_filter_spec_bcj(**spec)
		except TypeError:
			raise ValueError("Invalid...")
	else:
		raise ValueError("Invalid %d" % (ret.id,))

	ret.options = options
	_owns[ret] = options
	return ret

def _encode_filter_properties(filterspec):
	filter = parse_filter_spec(filterspec)
	size = ffi.new("uint32_t*")
	catch_lzma_error(m.lzma_properties_size, size, filter)
	result = ffi.new('char[]', size[0])
	catch_lzma_error(m.lzma_properties_encode, filter, result)
	return ffi.buffer(result)[:]

def parse_filter_chain_spec(filterspecs):
	if len(filterspecs) > m.LZMA_FILTERS_MAX:
		raise ValueError("Too...")
	filters = ffi.new('lzma_filter[]', m.LZMA_FILTERS_MAX+1)
	_owns[filters] = children = []
	for i in range(m.LZMA_FILTERS_MAX+1):
		try:
			filterspec = filterspecs[i]
		except IndexError:
			filters[i].id == m.LZMA_VLI_UNKNOWN
		else:
			filter = parse_filter_spec(filterspecs[i])
			children.append(filter)
			filters[i].id = filter.id
			filters[i].options = filter.options
	return filters

def build_filter_spec(filter):
	spec = {'id': filter.id}
	def add_opts(options_type, *opts):
		options = ffi.cast('%s*' % (options_type,), filter.options)
		for v in opts:
			spec[v] = getattr(options, v)
	if filter.id == m.LZMA_FILTER_LZMA1:
		add_opts('lzma_options_lzma', 'lc', 'lp', 'pb', 'dict_size')
	elif filter.id == m.LZMA_FILTER_LZMA2:
		add_opts('lzma_options_lzma', 'dict_size')
	elif filter.id == m.LZMA_FILTER_DELTA:
		add_opts('lzma_options_delta', 'dist')
	elif filter.id in BCJ_FILTERS:
		add_opts('lzma_options_bcj', 'start_offset')
	else:
		raise ValueError("Invalid...")
	return spec

def _decode_filter_properties(filter_id, encoded_props):
	filter = ffi.new('lzma_filter*')
	filter.id = filter_id
	catch_lzma_error(m.lzma_properties_decode,
		filter, ffi.NULL, encoded_props, len(encoded_props))
	try:
		return build_filter_spec(filter)
	finally:
		m.free(filter.options)

class Allocator(object):
	def __init__(self):
		self.owns = {}
		self.lzma_allocator = ffi.new('lzma_allocator*')
		alloc = self.owns['a'] = ffi.callback("void*(void*, size_t, size_t)", self.__alloc)
		free = self.owns['b'] = ffi.callback("void(void*, void*)", self.__free)
		self.lzma_allocator.alloc = alloc
		self.lzma_allocator.free = free
		self.lzma_allocator.opaque = ffi.NULL
		#m._pylzma_allocator_init2(self.lzma_allocator, alloc, free)
	def __alloc(self, _opaque, _nmemb, size):
		new_mem = ffi.new('char[]', size)
		self.owns[self._addr(new_mem)] = new_mem
		return new_mem
	def _addr(self, ptr):
		return long(ffi.cast('uintptr_t', ptr))
	def __free(self, _opaque, ptr):
		if self._addr(ptr) == 0L: return
		del self.owns[self._addr(ptr)]

class LZMADecompressor(object):
	def __init__(self, format=FORMAT_AUTO, memlimit=None, filters=None):
		decoder_flags = m.LZMA_TELL_ANY_CHECK | m.LZMA_TELL_NO_CHECK
		#decoder_flags = 0
		if memlimit is not None:
			if format == FORMAT_RAW:
				raise ValueError("Cannot sp...")
			#memlimit = long(memlimit)
		else:
			memlimit = m.UINT64_MAX
		if format == FORMAT_RAW and filters is None:
			raise ValueError("Must...")
		elif format != FORMAT_RAW and filters is not None:
			raise ValueError("Cannot...")
		self.lock = threading.Lock()
		self.check = CHECK_UNKNOWN
		self.unused_data = b''
		self.eof = False
		self.lzs = _new_lzma_stream()
		self.allocator = Allocator()
		#self.lzs.allocator = self.allocator.lzma_allocator
		if format == FORMAT_AUTO:
			catch_lzma_error(m.lzma_auto_decoder, self.lzs, memlimit, decoder_flags)
		elif format == FORMAT_XZ:
			catch_lzma_error(m.lzma_stream_decoder, self.lzs, memlimit, decoder_flags)
		elif format == FORMAT_ALONE:
			self.check = CHECK_NONE
			catch_lzma_error(m.lzma_alone_decoder, self.lzs, memlimit)
		elif format == FORMAT_RAW:
			self.check = CHECK_NONE
			raise NotImplementedError
		else:
			raise ValueError("invalid...")

	def decompress(self, data):
		with self.lock:
			if self.eof:
				raise EOFError("Already...")
			return self._decompress(data)

	def _decompress(self, data):
		BUFSIZ = 8192

		lzs = self.lzs

		lzs.next_in = in_ = ffi.new('char[]', memoryview(data).tobytes())
		lzs.avail_in = len(data)
		outs = [ffi.new('char[]', BUFSIZ)]
		lzs.next_out, = outs
		lzs.avail_out = BUFSIZ

		# siz := len(outs[-1])
		siz = BUFSIZ

		while True:
			next_out_pos = int(ffi.cast('intptr_t', lzs.next_out))
			ret = catch_lzma_error(m.lzma_code, lzs, m.LZMA_RUN)
			data_size = int(ffi.cast('intptr_t', lzs.next_out)) - next_out_pos
			if ret in (m.LZMA_NO_CHECK, m.LZMA_GET_CHECK):
				self.check = m.lzma_get_check(lzs)
			if ret == m.LZMA_STREAM_END:
				self.eof = True
				if lzs.avail_in > 0:
					self.unused_data = ffi.buffer(lzs.next_in, lzs.avail_in)[:]
				break
			elif lzs.avail_in == 0:
				# it ate everything
				break
			elif lzs.avail_out == 0:
				# ran out of space in the output buffer
				#siz = (BUFSIZ << 1) + 6
				siz = 512
				outs.append(ffi.new('char[]', siz))
				lzs.next_out = outs[-1]
				lzs.avail_out = siz
		last_out = outs.pop()
		last_out_piece = ffi.buffer(last_out[0:siz-lzs.avail_out])[:]

		return b''.join(ffi.buffer(nn)[:] for nn in outs) + last_out_piece

class LZMACompressor(object):
	def __init__(self, format=FORMAT_XZ, check=-1, preset=None, filters=None):
		if format != FORMAT_XZ and check not in (-1, m.LZMA_CHECK_NONE):
			raise ValueError("Integrity...")
		if preset is not None and filters is not None:
			raise ValueError("Cannot...")
		self.lock = threading.Lock()
		self.flushed = 0
		self.lzs = _new_lzma_stream()
		self.allocator = Allocator()
		#self.lzs.allocator = self.allocator.lzma_allocator
		if format == FORMAT_XZ:
			if filters is None:
				if preset is None:
					preset = m.LZMA_PRESET_DEFAULT
				if check == -1:
					check = m.LZMA_CHECK_CRC64
				catch_lzma_error(m.lzma_easy_encoder, self.lzs,
					preset, check)
			else:
				filters = parse_filter_chain_spec(filters)
				catch_lzma_error(m.lzma_stream_encoder, self.lzs,
					filters, check)
		elif format == FORMAT_ALONE:
			raise NotImplementedError
		elif format == FORMAT_RAW:
			if filters is None:
				raise ValueError("Must...")
			raise NotImplementedError
		else:
			raise ValueError("Invalid...")

	def compress(self, data):
		with self.lock:
			if self.flushed:
				raise ValueError("Compressor...")
			return self._compress(data)

	def _compress(self, data, action=m.LZMA_RUN):
		BUFSIZ = 8192

		lzs = self.lzs

		lzs.next_in = input_ = ffi.new('char[]', memoryview(data).tobytes())
		lzs.avail_in = len(data)
		outs = [ffi.new('char[]', BUFSIZ)]
		lzs.next_out, = outs
		lzs.avail_out = BUFSIZ

		siz = BUFSIZ

		while True:
			next_out_pos = int(ffi.cast('intptr_t', lzs.next_out))
			ret = catch_lzma_error(m.lzma_code, lzs, action)
			data_size = int(ffi.cast('intptr_t', lzs.next_out)) - next_out_pos
			if (action == m.LZMA_RUN and lzs.avail_in == 0) or \
				(action == m.LZMA_FINISH and ret == m.LZMA_STREAM_END):
				break
			elif lzs.avail_out == 0:
				# ran out of space in the output buffer
				#siz = (BUFSIZ << 1) + 6
				siz = 512
				outs.append(ffi.new('char[]', siz))
				lzs.next_out = outs[-1]
				lzs.avail_out = siz
		last_out = outs.pop()
		last_out_piece = ffi.buffer(last_out[0:siz-lzs.avail_out])[:]

		return b''.join(ffi.buffer(nn)[:] for nn in outs) + last_out_piece

	def flush(self):
		with self.lock:
			if self.flushed:
				raise ValueError("Repeated...")
			self.flushed = 1
			return self._compress(b'', action=m.LZMA_FINISH)

#errors = 18
