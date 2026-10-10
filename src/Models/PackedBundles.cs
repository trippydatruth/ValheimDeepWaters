using System;
using System.IO;
using UnityEngine;

namespace ValheimDeepWaters
{
    /// <summary>
    /// Released bundles are packed (.vdwpak): the .bundle's bytes scrambled with a fixed keystream, so asset
    /// rippers can't open the models and textures straight from the Models folder. They're read back through
    /// <see cref="PackStream"/>, which unscrambles as Unity streams the bundle in (nothing is held in memory twice).
    /// This only stops casual ripping: the key is in this DLL. package.ps1 does the packing with the same scheme.
    /// </summary>
    internal static class PackedBundles
    {
        public const string Extension = ".vdwpak";
        private const int PadSize = 4096;
        private static readonly byte[] Pad = BuildPad();

        /// <summary>
        /// The keystream: a 4 KB pad from a xorshift generator, varied per 4 KB block so it doesn't simply repeat.
        /// Must match package.ps1.
        /// </summary>
        private static byte[] BuildPad()
        {
            var pad = new byte[PadSize];
            uint x = 0x9E3779B9u ^ 0x56445750u;   // "VDWP"
            for (int i = 0; i < PadSize; i++)
            {
                x ^= x << 13; x ^= x >> 17; x ^= x << 5;
                pad[i] = (byte)(x >> 24);
            }
            return pad;
        }

        internal static byte KeyAt(long pos) => (byte)(Pad[pos % PadSize] ^ (byte)((pos / PadSize) * 167));

        /// <summary>Loads a packed bundle, keeping its stream open for as long as the bundle is (Unity reads it lazily).</summary>
        public static AssetBundle? Load(string path)
        {
            var stream = new PackStream(path);
            var bundle = AssetBundle.LoadFromStream(stream);
            if (bundle == null) stream.Dispose();
            return bundle;
        }

        /// <summary>A read-only, seekable view of a packed file that unscrambles the bytes as they're read.</summary>
        private sealed class PackStream : Stream
        {
            private readonly FileStream _file;
            public PackStream(string path) { _file = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read, 1 << 16); }

            public override int Read(byte[] buffer, int offset, int count)
            {
                long start = _file.Position;
                int n = _file.Read(buffer, offset, count);
                for (int i = 0; i < n; i++) buffer[offset + i] ^= KeyAt(start + i);
                return n;
            }

            public override long Seek(long offset, SeekOrigin origin) => _file.Seek(offset, origin);
            public override long Position { get => _file.Position; set => _file.Position = value; }
            public override long Length => _file.Length;
            public override bool CanRead => true;
            public override bool CanSeek => true;
            public override bool CanWrite => false;
            public override void Flush() { }
            public override void SetLength(long value) => throw new NotSupportedException();
            public override void Write(byte[] buffer, int offset, int count) => throw new NotSupportedException();
            protected override void Dispose(bool disposing) { if (disposing) _file.Dispose(); base.Dispose(disposing); }
        }
    }
}
