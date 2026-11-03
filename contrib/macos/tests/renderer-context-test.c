#include <glib-object.h>
#include <cairo.h>
#include <pango/pangocairo.h>

/* Opaque public API; avoid unrelated Lepton object headers in this probe. */
extern GObject *eda_renderer_new(cairo_t *, PangoContext *);

int main(void) {
  cairo_surface_t *surface = cairo_image_surface_create(CAIRO_FORMAT_ARGB32, 32, 32);
  cairo_t *cr = cairo_create(surface);
  GObject *renderer = eda_renderer_new(cr, NULL);
  for (int i = 0; i < 100; i++) {
    g_object_set(renderer, "cairo-context", cr, NULL);
    g_assert_cmpuint(cairo_get_reference_count(cr), >, 1);
    g_object_set(renderer, "cairo-context", NULL, NULL);
    cairo_t *stored = cr;
    g_object_get(renderer, "cairo-context", &stored, NULL);
    g_assert_null(stored);
    g_assert_cmpuint(cairo_get_reference_count(cr), ==, 1);
  }
  g_object_unref(renderer);
  g_assert_cmpuint(cairo_get_reference_count(cr), ==, 1);
  cairo_destroy(cr);
  g_assert_cmpuint(cairo_surface_get_reference_count(surface), ==, 1);
  cairo_surface_destroy(surface);
  g_print("PASS: 100 context attach/reuse/release cycles; no retained frame context\n");
  return 0;
}
