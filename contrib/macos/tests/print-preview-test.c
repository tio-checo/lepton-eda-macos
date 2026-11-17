/* Run the real GTK preview/export renderer. Build PREVIEW_INTERPOSER as a
 * test-only dylib to capture native launch or inject a launch failure.
 */
#include <gtk/gtk.h>
#include <string.h>

#ifdef PREVIEW_INTERPOSER
static gboolean
capture_launch (const gchar *uri, GAppLaunchContext *context, GError **error)
{
  const gchar *capture = g_getenv ("LEPTON_TEST_CAPTURE");
  gchar *path = g_filename_from_uri (uri, NULL, NULL);
  gchar *bytes = NULL;
  gsize length = 0;
  g_assert_nonnull (capture);
  g_assert_nonnull (path);
  g_assert_true (g_file_get_contents (path, &bytes, &length, NULL));
  g_assert_cmpuint (length, >, 100);
  g_assert_cmpmem (bytes, 5, "%PDF-", 5);
  g_assert_cmpmem (bytes + length - 6, 6, "%%EOF\n", 6);
  g_assert_true (g_file_set_contents (capture, uri, -1, NULL));
  gchar *copy = g_strconcat (capture, ".pdf", NULL);
  g_assert_true (g_file_set_contents (copy, bytes, length, NULL));
  g_free (copy);
  g_free (bytes);
  g_free (path);
  if (g_getenv ("LEPTON_TEST_LAUNCH_FAIL"))
    {
      g_set_error_literal (error, G_IO_ERROR, G_IO_ERROR_FAILED,
                           "Injected PDF launch failure");
      return FALSE;
    }
  return TRUE;
}

#ifdef LEPTON_PREVIEW_FROM_DIALOG
static GtkPrintOperationResult
preview_dialog (GtkPrintOperation *operation, GtkPrintOperationAction action,
                GtkWindow *parent, GError **error)
{
  g_assert_cmpint (action, ==, GTK_PRINT_OPERATION_ACTION_PRINT_DIALOG);
  GtkPrintOperationResult result = gtk_print_operation_run (
    operation, GTK_PRINT_OPERATION_ACTION_PREVIEW, parent, error);
  const gchar *report = g_getenv ("LEPTON_TEST_PRINT_RESULT");
  gchar *text = g_strdup_printf ("result=%d\nerror=%s\n", result,
                                 error && *error ? (*error)->message : "none");
  g_assert_true (g_file_set_contents (report, text, -1, NULL));
  g_free (text);
  return result;
}
#endif

__attribute__((used, section("__DATA,__interpose")))
static const struct { const void *replacement, *original; } interpose[] = {
  { (const void *) capture_launch, (const void *) g_app_info_launch_default_for_uri },
#ifdef LEPTON_PREVIEW_FROM_DIALOG
  { (const void *) preview_dialog, (const void *) gtk_print_operation_run }
#endif
};
#else
static guint drawn;

static void
draw_page (GtkPrintOperation *operation, GtkPrintContext *context,
           gint page, gpointer data)
{
  cairo_t *cr = gtk_print_context_get_cairo_context (context);
  drawn++;
  g_assert_cmpint (page, ==, 0);
  cairo_set_source_rgb (cr, 0.05, 0.2, 0.7);
  cairo_set_line_width (cr, 2.5);
  cairo_rectangle (cr, 12, 18, gtk_print_context_get_width (context) - 24,
                   gtk_print_context_get_height (context) - 36);
  cairo_stroke (cr);
  cairo_move_to (cr, 40, 60);
  cairo_set_font_size (cr, 18);
  cairo_show_text (cr, "Lepton EDA print preview / A4 landscape / 85%");
}

int
main (int argc, char **argv)
{
  gboolean exporting = argc == 2;
  gtk_init (&argc, &argv);
  GtkPrintOperation *op = gtk_print_operation_new ();
  GtkPageSetup *setup = gtk_page_setup_new ();
  GtkPaperSize *paper = gtk_paper_size_new (GTK_PAPER_NAME_A4);
  gtk_page_setup_set_paper_size_and_default_margins (setup, paper);
  gtk_page_setup_set_orientation (setup, GTK_PAGE_ORIENTATION_LANDSCAPE);
  gtk_print_operation_set_default_page_setup (op, setup);
  gtk_print_operation_set_n_pages (op, 1);
  gtk_print_operation_set_unit (op, GTK_UNIT_POINTS);
  GtkPrintSettings *settings = gtk_print_settings_new ();
  gtk_print_settings_set_scale (settings, 85);
  gtk_print_operation_set_print_settings (op, settings);
  g_signal_connect (op, "draw-page", G_CALLBACK (draw_page), NULL);
  if (exporting)
    gtk_print_operation_set_export_filename (op, argv[1]);
  GError *error = NULL;
  GtkPrintOperationResult result = gtk_print_operation_run (
    op, exporting ? GTK_PRINT_OPERATION_ACTION_EXPORT : GTK_PRINT_OPERATION_ACTION_PREVIEW,
    NULL, &error);
  g_print ("result=%d\ndrawn=%u\nerror=%s\n", result, drawn,
           error ? error->message : "none");
  g_clear_error (&error);
  gtk_paper_size_free (paper);
  g_object_unref (settings);
  g_object_unref (setup);
  g_object_unref (op);
  return 0;
}
#endif
