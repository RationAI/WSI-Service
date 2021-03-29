from cffi import FFI

ffi = FFI()
ffi.cdef(
    """
    int interpolate_tile(double * in_buffer, double * out_buffer, 
        int64_t in_size_x, int64_t in_size_y, 
        int64_t out_size_x, int64_t out_size_y, 
        int numChannels, 
        int64_t in_start_px_x, int64_t in_start_px_y, int64_t out_start_px_x, int64_t out_start_px_y, double * WR, double * WTInv,
        double * deformation_x, double * deformation_y, double * Wdef, double * Wdef_inv, int size_def_x, int size_def_y);
"""
)

ffi.set_source(
    "_interpolate",
    r"""
    #include "interpolate.h"
    
""",
    sources=["interpolate.cpp"],
    source_extension=".cpp",
    libraries=["m"],
)

if __name__ == "__main__":
    ffi.compile(verbose=True)
