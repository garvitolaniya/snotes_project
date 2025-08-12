# File: sdoc_importer.py
# This is the definitive version with the corrected identifier location.

import zipfile
import struct
import gzip
import zlib
from .model import SdocDocument, SdocPage, SdocStroke, SdocPoint

class SdocImporter:
    def import_sdoc(self, path: str) -> SdocDocument:
        doc = SdocDocument()
        try:
            with zipfile.ZipFile(path, 'r') as sdoc_zip:
                for file_info in sdoc_zip.infolist():
                    if file_info.filename.endswith('.page'):
                        page_content = sdoc_zip.read(file_info)
                        page = self._parse_page(page_content)
                        if page:
                            doc.pages.append(page)
        except (zipfile.BadZipFile, FileNotFoundError):
            raise IOError("Failed to open or read the sdocx file.")
        return doc

    def _parse_page(self, content: bytes) -> SdocPage:
        page = SdocPage()
        try:
            content = gzip.decompress(content)
        except (gzip.BadGzipFile, EOFError, zlib.error):
            pass

        offset = 16
        while offset < len(content):
            try:
                chunk_type, chunk_length = struct.unpack_from('<II', content, offset)
                offset += 8
                chunk_data_offset = offset
                if chunk_length == 0: break
                if chunk_type == 2:
                    self._parse_chunk_type_2(content[chunk_data_offset:chunk_data_offset + chunk_length], page)
                offset = chunk_data_offset + chunk_length
            except (struct.error, IndexError):
                break
        return page

    def _parse_chunk_type_2(self, content: bytes, page: SdocPage):
        offset = 0
        while offset < len(content):
            try:
                header = content[offset:offset + 16]
                if not header or len(header) < 16: break
                object_size = struct.unpack_from('<I', header, 4)[0]
                if object_size == 0: break
                
                # --- THIS IS THE FINAL FIX ---
                # Check for the 0x930A identifier at the CORRECT offset (4th byte)
                if header[4:6] == b'\x93\x0A':
                    stroke_content = content[offset : offset + object_size]
                    stroke = self._parse_stroke(stroke_content)
                    if stroke and stroke.points:
                        page.strokes.append(stroke)
                
                offset += object_size
            except (struct.error, IndexError):
                break

    def _parse_stroke(self, content: bytes) -> SdocStroke:
        stroke = SdocStroke()
        try:
            header = content[0:48] # Read enough header data
            # size is at offset 4, num_points is at offset 8, props_flag is at offset 12
            _, size, num_points, props_flag = struct.unpack_from('<IIII', header)
            
            point_data_offset = 0x30 # 48 bytes
            
            if props_flag == 0x00006900: # The flag from your diagnostic log
                 bytes_per_point = 24
                 format_string = '<ffffff' # x, y, p, tiltX, tiltY, timestamp
            else: # Fallback for other common formats
                bytes_per_point = 12
                format_string = '<fff' # x, y, p

            offset = point_data_offset
            for i in range(num_points):
                if offset + bytes_per_point > len(content): break
                
                point_data = struct.unpack_from(format_string, content, offset)
                x, y, p = point_data[0], point_data[1], point_data[2]
                t = point_data[5] if bytes_per_point == 24 else i
                
                stroke.points.append(SdocPoint(x, y, p, t))
                offset += bytes_per_point
            return stroke
        except (struct.error, IndexError):
            return stroke