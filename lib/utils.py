
import struct
import re
from enum import Enum
from typing import Optional, List

class AudioUtility:
    @staticmethod
    def save_binary_file(file_name: str, data: bytes):
        with open(file_name, "wb") as f:
            f.write(data)
        print(f"File saved to: {file_name}")

    @staticmethod
    def parse_audio_mime_type(mime_type: str) -> dict:
        bits_per_sample, rate = 16, 24000
        parts = mime_type.split(";")
        for param in parts:
            param = param.strip().lower()
            if param.startswith("rate="):
                rate = int(param.split("=")[1])
            elif param.startswith("audio/l"):
                bits_per_sample = int(param[7:])
        return {"bits_per_sample": bits_per_sample, "rate": rate}

    @staticmethod
    def convert_to_wav(audio_data: bytes, mime_type: str) -> bytes:
        parameters = AudioUtility.parse_audio_mime_type(mime_type)
        bits_per_sample = parameters["bits_per_sample"]
        sample_rate = parameters["rate"]
        num_channels = 1
        data_size = len(audio_data)
        bytes_per_sample = bits_per_sample // 8
        block_align = num_channels * bytes_per_sample
        byte_rate = sample_rate * block_align
        chunk_size = 36 + data_size

        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", chunk_size, b"WAVE", b"fmt ", 16, 1,
            num_channels, sample_rate, byte_rate, block_align, bits_per_sample,
            b"data", data_size
        )
        return header + audio_data


