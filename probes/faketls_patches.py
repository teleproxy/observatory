"""Patches for TelethonFakeTLS upstream bugs.

1. read_server_hello: upstream only reads the first encrypted record,
   but the proxy computes HMAC over all records.
2. FakeTLSStreamWriter: upstream never sends CCS (ChangeCipherSpec)
   before the first data record, but the proxy requires it.

Adapted from teleproxy's test_direct_e2e.py.
"""

import asyncio


def patch_telethon_faketls():
    """Apply patches to TelethonFakeTLS.  Call once before creating clients."""
    import TelethonFakeTLS.FakeTLS.TLSInOut as tls_io

    async def _read_server_hello(self):
        buf = bytearray(await self.upstream.readexactly(133))
        while True:
            try:
                header = await asyncio.wait_for(
                    self.upstream.readexactly(5), timeout=0.5
                )
            except (asyncio.TimeoutError, EOFError):
                break
            buf += header
            if header[:3] != b"\x17\x03\x03":
                break
            rec_len = int.from_bytes(header[3:5], "big")
            buf += await self.upstream.readexactly(rec_len)
        return bytes(buf)

    tls_io.FakeTLSStreamReader.read_server_hello = _read_server_hello

    _orig_write = tls_io.FakeTLSStreamWriter.write
    _ccs_sent_writers = set()

    def _writer_write_with_ccs(self, data, extra={}):
        if id(self) not in _ccs_sent_writers:
            _ccs_sent_writers.add(id(self))
            self.upstream.write(b"\x14\x03\x03\x00\x01\x01")
        return _orig_write(self, data, extra)

    tls_io.FakeTLSStreamWriter.write = _writer_write_with_ccs
