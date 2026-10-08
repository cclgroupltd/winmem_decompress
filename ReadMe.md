# winmem_decompress_lz4.py

Windows 11 [since 24H2](https://github.com/ufrisk/MemProcFS/blob/a81e7960d6f17a4adfc77c080f94e631d74b2fb9/vmm/mm/mm_win.c#L1065) uses the LZ4 algorithm to compress memory pages.

`winmem_decompress_lz4.py` is based on Maxim Suhanov's `winmem_decompress.py`. It replaces the LZ77 decompressor present in the original script with an LZ4 decompressor based on python-lz4. It uses the [same strategy as the original version](https://dfir.ru/2018/09/08/memory-compression-and-forensics/) and therefore has similar limitations.

## Changes
* Replace LZ77DecompressBuffer with an LZ4 decompressor (requires python-lz4).
* Run more than 4 parallel tasks.
* Save the output to a specified file.
* Print a progress indicator.


----


# winmem_decompress.py

This program tries to extract compressed memory pages from page-aligned data.
Every decompressed page is written to the standard output.

Such compressed memory pages can be found in virtual memory of Windows 8.1 & 10 operating systems.

## Input data

The following types of data can be processed:
* page files;
* crash dumps;
* memory dumps (raw).

## Output data

Every decompressed page should be 4096 bytes in length.
If a decompressed page is truncated (smaller than that), null bytes are used as padding.

Since the program utilizes the brute-force approach to decompress memory pages, many false positives are expected.

## Speed

*The program is very slow.*
The following processing times were seen in a test based on [the 2018 Lone Wolf Scenario](https://digitalcorpora.org/corpora/scenarios/2018-lone-wolf-scenario):
* a page file (2944 MiB): 4 minutes;
* a memory dump (17126 MiB): 6 hours.

## License

The program is made available under the terms of the GNU GPL, version 3.
See the 'License.txt' file.
