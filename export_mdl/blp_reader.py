import struct
import os
import tempfile
import numpy as np


def _rgb565(c):
    r = ((c >> 11) & 0x1F) * 255 // 31
    g = ((c >> 5) & 0x3F) * 255 // 63
    b = (c & 0x1F) * 255 // 31
    return r, g, b


def _decode_dxt1(data, w, h):
    pixels = np.zeros((h, w, 4), dtype=np.uint8)
    bw, bh = (w + 3) // 4, (h + 3) // 4
    off = 0
    for by in range(bh):
        for bx in range(bw):
            if off + 8 > len(data):
                return pixels
            c0, c1 = struct.unpack_from('<HH', data, off)
            off += 4
            r0, g0, b0 = _rgb565(c0)
            r1, g1, b1 = _rgb565(c1)
            colors = [(r0, g0, b0, 255), (r1, g1, b1, 255)]
            if c0 > c1:
                colors.append(((2*r0+r1)//3, (2*g0+g1)//3, (2*b0+b1)//3, 255))
                colors.append(((r0+2*r1)//3, (g0+2*g1)//3, (b0+2*b1)//3, 255))
            else:
                colors.append(((r0+r1)//2, (g0+g1)//2, (b0+b1)//2, 255))
                colors.append((0, 0, 0, 0))
            bits = struct.unpack_from('<I', data, off)[0]
            off += 4
            for py in range(4):
                for px in range(4):
                    x, y = bx*4+px, by*4+py
                    if x < w and y < h:
                        pixels[y, x] = colors[(bits >> (2*(py*4+px))) & 3]
    return pixels


def _decode_dxt3(data, w, h):
    pixels = np.zeros((h, w, 4), dtype=np.uint8)
    bw, bh = (w + 3) // 4, (h + 3) // 4
    off = 0
    for by in range(bh):
        for bx in range(bw):
            if off + 16 > len(data):
                return pixels
            alpha_data = data[off:off+8]
            off += 8
            c0, c1 = struct.unpack_from('<HH', data, off)
            off += 4
            r0, g0, b0 = _rgb565(c0)
            r1, g1, b1 = _rgb565(c1)
            colors = [(r0,g0,b0), (r1,g1,b1),
                      ((2*r0+r1)//3,(2*g0+g1)//3,(2*b0+b1)//3),
                      ((r0+2*r1)//3,(g0+2*g1)//3,(b0+2*b1)//3)]
            bits = struct.unpack_from('<I', data, off)[0]
            off += 4
            for py in range(4):
                for px in range(4):
                    x, y = bx*4+px, by*4+py
                    if x < w and y < h:
                        ci = (bits >> (2*(py*4+px))) & 3
                        ai = py*4+px
                        abyte = alpha_data[ai//2]
                        a = ((abyte >> ((ai % 2)*4)) & 0xF) * 17
                        pixels[y, x] = (*colors[ci], a)
    return pixels


def _decode_dxt5(data, w, h):
    pixels = np.zeros((h, w, 4), dtype=np.uint8)
    bw, bh = (w + 3) // 4, (h + 3) // 4
    off = 0
    for by in range(bh):
        for bx in range(bw):
            if off + 16 > len(data):
                return pixels
            a0, a1 = data[off], data[off+1]
            off += 2
            abits = int.from_bytes(data[off:off+6], 'little')
            off += 6
            alphas = [a0, a1]
            if a0 > a1:
                for i in range(1, 7):
                    alphas.append(((7-i)*a0 + i*a1) // 7)
            else:
                for i in range(1, 5):
                    alphas.append(((5-i)*a0 + i*a1) // 5)
                alphas.extend([0, 255])
            c0, c1 = struct.unpack_from('<HH', data, off)
            off += 4
            r0, g0, b0 = _rgb565(c0)
            r1, g1, b1 = _rgb565(c1)
            colors = [(r0,g0,b0), (r1,g1,b1),
                      ((2*r0+r1)//3,(2*g0+g1)//3,(2*b0+b1)//3),
                      ((r0+2*r1)//3,(g0+2*g1)//3,(b0+2*b1)//3)]
            bits = struct.unpack_from('<I', data, off)[0]
            off += 4
            for py in range(4):
                for px in range(4):
                    x, y = bx*4+px, by*4+py
                    if x < w and y < h:
                        ci = (bits >> (2*(py*4+px))) & 3
                        ai = py*4+px
                        a = alphas[(abits >> (3*ai)) & 7]
                        pixels[y, x] = (*colors[ci], a)
    return pixels


def load_blp(filepath):
    """Load a BLP file. Returns (width, height, flat_rgba_float_list) or ('jpeg', temp_path) or None."""
    with open(filepath, 'rb') as f:
        magic = f.read(4)
        if magic not in (b'BLP2', b'BLP1'):
            return None

        if magic == b'BLP2':
            compression, alpha_depth, alpha_type, has_mips = struct.unpack('<BBBB', f.read(4))
            width, height = struct.unpack('<II', f.read(8))
            mip_offsets = struct.unpack('<16I', f.read(64))
            mip_sizes = struct.unpack('<16I', f.read(64))

            if compression == 1:
                palette = []
                for _ in range(256):
                    b, g, r, a = struct.unpack('<BBBB', f.read(4))
                    palette.append((r, g, b, a))
                f.seek(mip_offsets[0])
                indices = f.read(mip_sizes[0])
                pixel_count = width * height
                pixels = np.zeros((pixel_count, 4), dtype=np.uint8)

                color_indices = indices[:pixel_count]
                for i in range(min(pixel_count, len(color_indices))):
                    r, g, b, pa = palette[color_indices[i]]
                    pixels[i] = (r, g, b, 255)

                if alpha_depth == 8 and len(indices) >= pixel_count * 2:
                    for i in range(pixel_count):
                        pixels[i, 3] = indices[pixel_count + i]
                elif alpha_depth == 1:
                    alpha_start = pixel_count
                    for i in range(pixel_count):
                        byte_idx = alpha_start + i // 8
                        if byte_idx < len(indices):
                            pixels[i, 3] = 255 if (indices[byte_idx] >> (i % 8)) & 1 else 0
                elif alpha_depth == 4:
                    alpha_start = pixel_count
                    for i in range(pixel_count):
                        byte_idx = alpha_start + i // 2
                        if byte_idx < len(indices):
                            if i % 2 == 0:
                                pixels[i, 3] = (indices[byte_idx] & 0x0F) * 17
                            else:
                                pixels[i, 3] = ((indices[byte_idx] >> 4) & 0x0F) * 17

                pixels = pixels.reshape((height, width, 4))

            elif compression == 2:
                f.seek(mip_offsets[0])
                data = f.read(mip_sizes[0])
                if alpha_type == 0:
                    pixels = _decode_dxt1(data, width, height)
                elif alpha_type == 1:
                    pixels = _decode_dxt3(data, width, height)
                else:
                    pixels = _decode_dxt5(data, width, height)

            elif compression == 3:
                f.seek(mip_offsets[0])
                data = f.read(width * height * 4)
                pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
                pixels = pixels[:, :, [2, 1, 0, 3]]
            else:
                return None

            flat = (pixels.reshape(-1).astype(np.float32) / 255.0).tolist()
            return width, height, flat

        else:
            # BLP1
            compression = struct.unpack('<I', f.read(4))[0]
            alpha_depth = struct.unpack('<I', f.read(4))[0]
            width = struct.unpack('<I', f.read(4))[0]
            height = struct.unpack('<I', f.read(4))[0]
            flags = struct.unpack('<I', f.read(4))[0]
            has_mips = struct.unpack('<I', f.read(4))[0]
            mip_offsets = struct.unpack('<16I', f.read(64))
            mip_sizes = struct.unpack('<16I', f.read(64))

            if compression == 0:
                # JPEG - save to temp file for Blender to load
                jpeg_header_size = struct.unpack('<I', f.read(4))[0]
                jpeg_header = f.read(jpeg_header_size)
                f.seek(mip_offsets[0])
                mip_data = f.read(mip_sizes[0])
                full_jpeg = jpeg_header + mip_data

                tmp = os.path.join(tempfile.gettempdir(), '_blp_temp.jpg')
                with open(tmp, 'wb') as out:
                    out.write(full_jpeg)
                return 'jpeg', tmp

            elif compression == 1:
                palette = []
                for _ in range(256):
                    b, g, r, a = struct.unpack('<BBBB', f.read(4))
                    palette.append((r, g, b, a))
                f.seek(mip_offsets[0])
                indices = f.read(mip_sizes[0])
                pixel_count = width * height
                pixels = np.zeros((pixel_count, 4), dtype=np.uint8)
                for i in range(min(pixel_count, len(indices))):
                    pixels[i] = palette[indices[i]]
                pixels = pixels.reshape((height, width, 4))
                flat = (pixels.reshape(-1).astype(np.float32) / 255.0).tolist()
                return width, height, flat

            return None
