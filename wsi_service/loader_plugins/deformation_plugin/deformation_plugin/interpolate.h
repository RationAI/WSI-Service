// (C) 2021 Fraunhofer MEVIS. All rights reserved.
// Not for clinical use. Research use only.

#include <stdbool.h>

extern "C" int interpolate_tile(double *in_buffer, double *out_buffer,
                                int64_t in_size_x, int64_t in_size_y,
                                int64_t out_size_x, int64_t out_size_y,
                                int numChannels,
                                int64_t in_start_px_x, int64_t in_start_px_y, int64_t out_start_px_x, int64_t out_start_px_y, double *WR, double *WTInv,
                                double *deformation_x, double *deformation_y, double *Wdef, double *Wdef_inv, int size_def_x, int size_def_y);

double linearInterpPoint2D(int64_t m0, int64_t m1, const double *T, const double x_voxel, const double y_voxel, const double outOfBoundVal, bool *outOfBounds);