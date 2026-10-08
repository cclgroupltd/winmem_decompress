#!/usr/bin/env python3

# (c) Maxim Suhanov

# Modified by Arun Prasannan to support LZ4 compression for Windows 11 24H2.

import os
import sys
import time
import lz4.block
import multiprocessing

PROGRAM_VERSION = 'CCL-20261005'
PARALLEL_TASKS = multiprocessing.cpu_count() # The number of decompression tasks to run in parallel.

PAGE_SIZE = 4096
COMPRESSED_DATA_CHUNK_SIZE = 16

DECOMPRESSED_DATA_SIZE_MIN = PAGE_SIZE # Ignore decompressed data chunks which are smaller than this value.

PROGRESS_INTERVAL = 1024 * PAGE_SIZE # gap between progress updates

def LZ4DecompressBuffer(Buffer):
    """Try decompressing Buffer as an LZ4-compressed memory page.

    Return the first 4096-byte decompression found or empty bytes on failure.
    Lengths are tried in 16-byte aligned increments.
    """
    max_compressed_len = PAGE_SIZE - 1

    for length in range(COMPRESSED_DATA_CHUNK_SIZE, max_compressed_len + 1, COMPRESSED_DATA_CHUNK_SIZE):
        try:
            decompressed = lz4.block.decompress(Buffer[:length], uncompressed_size=PAGE_SIZE)
            if len(decompressed) == PAGE_SIZE:
                return decompressed
        except lz4.block.LZ4BlockError:
            continue

    return b""

def ScanBuffer(Buffer, pool):
    """Scan Buffer for compressed data chunks, yield every decompressed data chunk."""

    null_bytes_12 = b'\x00' * 12
    compressed_data_to_process = []

    pos = 0
    while pos < len(Buffer):
        compressed_data = Buffer[pos : pos + PAGE_SIZE]

        if not compressed_data.startswith(null_bytes_12): # Check if data starts with many null bytes.
            compressed_data_to_process.append(compressed_data)

        pos += COMPRESSED_DATA_CHUNK_SIZE # Compressed memory pages are stored in chunks.

    for decompressed_data in pool.imap_unordered(LZ4DecompressBuffer, compressed_data_to_process, chunksize=8):
        if len(decompressed_data) >= DECOMPRESSED_DATA_SIZE_MIN:
            yield decompressed_data

def ScanFile(FilePath, pool):
    """Scan a given file for compressed data chunks, yield every decompressed data chunk."""

    read_chunk_size = 32 * PAGE_SIZE

    with open(FilePath, 'rb') as file_obj:
        file_obj.seek(0, 2)
        file_size = file_obj.tell()

        file_pos = 0
        next_progress = PROGRESS_INTERVAL
        time_start = time.time()

        while file_pos < file_size:
            file_obj.seek(file_pos)
            buf = file_obj.read(read_chunk_size)

            for data in ScanBuffer(buf, pool):
                yield data

            if len(buf) != read_chunk_size:
                # End of a file or a read error.
                break

            file_pos += read_chunk_size

            if file_pos >= next_progress:
                elapsed = time.time() - time_start
                percent = (file_pos / file_size) * 100.0 if file_size else 0.0
                speed = (file_pos / (10 ** 6)) / elapsed if elapsed > 0 else 0
                remaining = file_size - file_pos
                eta = remaining / (file_pos / elapsed) if elapsed > 0 else 0
                print(f" progress: {percent:.2f}% ({file_pos}/{file_size} bytes, {speed:.1f} MB/s, ETA {eta:.1f}s)", file=sys.stderr)
                next_progress += PROGRESS_INTERVAL

def PrintUsage():
    """Print the usage information."""

    print('winmem_decompress (LZ4 version), version: {}'.format(PROGRAM_VERSION), file = sys.stderr)
    print('', file = sys.stderr)
    print('This program tries to extract compressed memory pages from page-aligned data.', file = sys.stderr)
    print('Every decompressed page is written to the output file.', file = sys.stderr)
    print('', file = sys.stderr)
    print('Usage: {} <input file> <output file>'.format(sys.argv[0]), file = sys.stderr)

if __name__ == '__main__':
    if len(sys.argv) < 3:
        PrintUsage()
        sys.exit(1)

    file_path = sys.argv[1]
    output_path = sys.argv[2]

    if not os.path.isfile(file_path):
        print('File doesn\'t exist: {}'.format(file_path), file = sys.stderr)
        sys.exit(1)

    print(f"Running {PARALLEL_TASKS} parallel tasks ...")
    pool = multiprocessing.Pool(processes=PARALLEL_TASKS)

    start_time = round(time.time())
    page_count = 0
    with open(output_path, "wb") as out_file:
        for data in ScanFile(file_path, pool):
            out_file.write(data)
            page_count += 1

    pool.close()
    pool.join()

    end_time = round(time.time())
    print(f"Processing done in {end_time - start_time} seconds; {page_count} pages decompressed.", file = sys.stderr)
