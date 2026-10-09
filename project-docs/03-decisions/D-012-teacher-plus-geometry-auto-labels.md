# D-012 · Auto-label with a teacher model corrected by geometry

- **Date:** 2026-10-06
- **Status:** Accepted

Mask2Former Swin-L (Mapillary Vistas: 65 classes, including lane markings,
crosswalks, manholes, curbs, terrain) labels frames offline; geometry
corrects raised areas to "other" and small flat "other" blobs inside road to
road. This gives large amounts of labels without hand labelling.

**Known cost:** the student inherits the teacher's mistakes (e.g. grass on the
road called road). Human labels are needed for forbidden surfaces.
