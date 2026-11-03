#include <pango/pangocairo.h>
#include <stdio.h>
int main(int argc, char **argv) {
  PangoFontMap *map = pango_cairo_font_map_get_default();
  PangoContext *context = pango_font_map_create_context(map);
  PangoLayout *layout = pango_layout_new(context);
  if (argc > 1) {
    PangoFontDescription *specified = pango_font_description_from_string(argv[1]);
    pango_layout_set_font_description(layout, specified);
    pango_font_description_free(specified);
  }
  /* A layout without an explicit font uses the context default. */
  const PangoFontDescription *desc = pango_layout_get_font_description(layout);
  fprintf(stderr, "layout font description: %p\n", (void *)desc);
  PangoFontMetrics *metrics = pango_context_get_metrics(context, desc, NULL);
  printf("descent: %d\n", pango_font_metrics_get_descent(metrics));
  pango_font_metrics_unref(metrics);
  g_object_unref(layout);
  g_object_unref(context);
  return 0;
}
