/* ReGreet presentation extension. Does not read or modify authentication data.
 * Centered presentation inspired by Noctalia Greeter; uses desktop theme assets.
 * Only activated inside the regreet executable; other children are untouched. */
#define _GNU_SOURCE
#include <gtk/gtk.h>
#include <math.h>
#include <string.h>
#include <unistd.h>

static void draw(GtkDrawingArea *area, cairo_t *cr, int w, int h, gpointer data) {
    (void)data;
    GdkRGBA fg;
    gtk_style_context_get_color(gtk_widget_get_style_context(GTK_WIDGET(area)), &fg);
    cairo_set_source_rgba(cr, 0, 0, 0, .32);
    cairo_paint(cr);
    (void)w; (void)h; (void)fg;
}

typedef struct { GtkWidget *clock, *panel, *hud, *time_label, *date_label; int width, height; } Layout;
static gboolean tick(GtkWidget *area, GdkFrameClock *clock, gpointer data) {
    Layout *l = data;
    int w = gtk_widget_get_width(area), h = gtk_widget_get_height(area);
    if (w != l->width || h != l->height) {
        l->width=w; l->height=h;
        gtk_widget_set_visible(l->clock, FALSE);
        gtk_widget_set_halign(l->panel, GTK_ALIGN_CENTER);
        gtk_widget_set_valign(l->panel, GTK_ALIGN_CENTER);
        gtk_widget_set_margin_top(l->panel, 0);
        gtk_widget_set_margin_start(l->panel, 12);
        gtk_widget_set_margin_end(l->panel, 12);
        gtk_widget_set_halign(l->hud, GTK_ALIGN_CENTER);
        gtk_widget_set_valign(l->hud, GTK_ALIGN_END);
        gtk_widget_set_margin_bottom(l->hud, MAX(16, h/24));
    }
    gint64 second = gdk_frame_clock_get_frame_time(clock)/1000000;
    gint64 previous = (gint64)(gintptr)g_object_get_data(G_OBJECT(area), "last-second");
    if (second != previous) {
        g_object_set_data(G_OBJECT(area), "last-second", (gpointer)(gintptr)second);
        GDateTime *now = g_date_time_new_now_local();
        char *time = g_date_time_format(now, "%H:%M");
        char *date = g_date_time_format(now, "%A, %B %e");
        gtk_label_set_text(GTK_LABEL(l->time_label), time);
        gtk_label_set_text(GTK_LABEL(l->date_label), date);
        g_free(time); g_free(date); g_date_time_unref(now);
        gtk_widget_queue_draw(area);
    }
    return G_SOURCE_CONTINUE;
}

/* Suppress only the informational automatic-session notice. Errors stay visible. */
static void quiet_session_notice(GObject *object, GParamSpec *pspec, gpointer data) {
    (void)object; (void)pspec;
    GtkWidget *label = data;
    const char *text = gtk_label_get_text(GTK_LABEL(label));
    if (!g_str_has_prefix(text, "Auto-selecting session ")) return;
    GtkWidget *bar = gtk_widget_get_ancestor(label, GTK_TYPE_INFO_BAR);
    if (bar) {
        GtkWidget *frame = gtk_widget_get_parent(bar);
        gtk_widget_set_visible(GTK_IS_FRAME(frame) ? frame : bar, FALSE);
    }
}

static void refine_controls(GtkWidget *widget) {
    if (GTK_IS_LABEL(widget) && gtk_widget_get_ancestor(widget, GTK_TYPE_INFO_BAR)) {
        g_signal_connect(widget, "notify::label", G_CALLBACK(quiet_session_notice), widget);
        GtkWidget *bar = gtk_widget_get_ancestor(widget, GTK_TYPE_INFO_BAR);
        g_signal_connect(gtk_widget_get_parent(bar), "notify::visible", G_CALLBACK(quiet_session_notice), widget);
        quiet_session_notice(NULL, NULL, widget);
    }
    if (GTK_IS_BUTTON(widget)) {
        const char *label = gtk_button_get_label(GTK_BUTTON(widget));
        const char *icon = g_strcmp0(label, "Reboot") == 0 ? "system-reboot-symbolic" :
                           g_strcmp0(label, "Power Off") == 0 ? "system-shutdown-symbolic" : NULL;
        if (icon) {
            char *description = g_strdup(label);
            GtkWidget *image = gtk_image_new_from_icon_name(icon);
            gtk_image_set_pixel_size(GTK_IMAGE(image), 20);
            gtk_button_set_child(GTK_BUTTON(widget), image);
            gtk_widget_add_css_class(widget, "power-symbol");
            gtk_widget_set_tooltip_text(widget, description);
            gtk_accessible_update_property(GTK_ACCESSIBLE(widget), GTK_ACCESSIBLE_PROPERTY_LABEL, description, -1);
            g_free(description);
        }
    }
    for (GtkWidget *child=gtk_widget_get_first_child(widget); child; child=gtk_widget_get_next_sibling(child))
        refine_controls(child);
}

static gboolean arrange(gpointer data) {
    GtkWindow *window = data;
    GtkWidget *overlay = gtk_window_get_child(window);
    if (!GTK_IS_OVERLAY(overlay)) return G_SOURCE_REMOVE;
    GtkWidget *panel=NULL, *clock=NULL, *hud=NULL;
    for (GtkWidget *c=gtk_widget_get_first_child(overlay); c; c=gtk_widget_get_next_sibling(c)) {
        if (GTK_IS_FRAME(c)) {
            if (GTK_IS_GRID(gtk_frame_get_child(GTK_FRAME(c)))) panel=c;
            else clock=c;
        } else if (GTK_IS_BOX(c)) hud=c;
    }
    /* Unknown layouts use ReGreet's original UI without modification. */
    if (!panel || !clock || !hud) { g_warning("Noctalia-inspired layout: unfamiliar ReGreet widgets; keeping default layout"); return G_SOURCE_REMOVE; }
    gtk_widget_add_css_class(panel, "noctalia-login");
    gtk_widget_add_css_class(clock, "noctalia-clock-fallback");
    gtk_widget_add_css_class(hud, "noctalia-hud");
    refine_controls(hud);
    GtkWidget *grid = gtk_frame_get_child(GTK_FRAME(panel));
    gtk_widget_set_size_request(grid, 320, -1);
    gtk_widget_set_margin_start(grid, 0); gtk_widget_set_margin_end(grid, 0);
    gtk_widget_set_margin_top(grid, 0); gtk_widget_set_margin_bottom(grid, 0);
    gtk_grid_set_row_spacing(GTK_GRID(grid), 8);
    gtk_grid_set_row_homogeneous(GTK_GRID(grid), FALSE);
    gtk_grid_set_column_homogeneous(GTK_GRID(grid), FALSE);
    gtk_grid_set_column_spacing(GTK_GRID(grid), 8);
    GList *children=NULL;
    for (GtkWidget *c=gtk_widget_get_first_child(grid); c; c=gtk_widget_get_next_sibling(c))
        children=g_list_prepend(children, g_object_ref(c));
    for (GList *item=children; item; item=item->next) {
        GtkWidget *c=item->data;
        int x,y,w,h; gtk_grid_query_child(GTK_GRID(grid),c,&x,&y,&w,&h);
        gtk_grid_remove(GTK_GRID(grid),c);
        gtk_widget_set_margin_top(c,0); gtk_widget_set_margin_bottom(c,0);
        gtk_widget_set_margin_start(c,0); gtk_widget_set_margin_end(c,0);
        gtk_widget_set_size_request(c,-1,-1);
        gtk_widget_set_vexpand(c,FALSE);
        gtk_widget_set_valign(c,GTK_ALIGN_CENTER);
        if (!GTK_IS_LABEL(c)) gtk_widget_set_halign(c,GTK_ALIGN_FILL);
        int row=y==0 ? 0 : y==3 ? 5 : (y-1)*2+(x==0 ? 1 : 2);
        gtk_grid_attach(GTK_GRID(grid),c,x==2 ? 1 : 0,row,(x==0 || y==3) ? 2 : 1,1);
        if (GTK_IS_LABEL(c)) {
            gtk_label_set_xalign(GTK_LABEL(c), y==0 ? .5 : 0);
            gtk_widget_add_css_class(c,y==0 ? "login-heading" : "field-caption");
        } else if (x==1) {
            gtk_widget_set_hexpand(c,TRUE);
        }
        if (GTK_IS_BOX(c)) {
            gtk_widget_set_margin_top(c,10);
            for (GtkWidget *button=gtk_widget_get_first_child(c); button; button=gtk_widget_get_next_sibling(button))
                if (gtk_widget_has_css_class(button,"suggested-action"))
                    gtk_widget_set_hexpand(button,TRUE);
        }
        g_object_unref(c);
    }
    g_list_free(children);
    GtkWidget *card=gtk_box_new(GTK_ORIENTATION_VERTICAL,0);
    GtkWidget *time_label=gtk_label_new(""), *date_label=gtk_label_new("");
    gtk_widget_add_css_class(time_label,"card-time");
    gtk_widget_add_css_class(date_label,"card-date");
    gtk_box_append(GTK_BOX(card),time_label);
    gtk_box_append(GTK_BOX(card),date_label);
    g_object_ref(grid);
    gtk_frame_set_child(GTK_FRAME(panel),NULL);
    gtk_box_append(GTK_BOX(card),grid);
    g_object_unref(grid);
    gtk_frame_set_child(GTK_FRAME(panel),card);
    GtkWidget *area=gtk_drawing_area_new();
    gtk_widget_set_hexpand(area, TRUE); gtk_widget_set_vexpand(area, TRUE);
    gtk_widget_set_can_target(area, FALSE);
    gtk_drawing_area_set_draw_func(GTK_DRAWING_AREA(area), draw, NULL, NULL);
    gtk_overlay_add_overlay(GTK_OVERLAY(overlay), area);
    gtk_widget_insert_after(area, overlay, gtk_overlay_get_child(GTK_OVERLAY(overlay)));
    Layout *l=g_new0(Layout, 1); l->panel=panel; l->clock=clock; l->hud=hud; l->time_label=time_label; l->date_label=date_label;
    gtk_widget_add_tick_callback(area, tick, l, g_free);
    g_message("Noctalia-inspired layout: integrated clock and stacked sign-in fields ready");
    return G_SOURCE_REMOVE;
}

static gboolean find_window(gpointer data) {
    (void)data;
    GListModel *windows=gtk_window_get_toplevels();
    for (guint i=0; i<g_list_model_get_n_items(windows); i++) {
        GtkWindow *window=g_list_model_get_item(windows, i);
        if (GTK_IS_APPLICATION_WINDOW(window) && GTK_IS_OVERLAY(gtk_window_get_child(window))) {
            /* Apply after ReGreet initializes GTK: startup settings may be replaced. */
            GtkSettings *settings = gtk_settings_get_default();
            g_object_set(settings, "gtk-cursor-theme-name", "GoogleDot-Black",
                         "gtk-cursor-theme-size", 20, NULL);
            char *cursor_theme = NULL; int cursor_size = 0;
            g_object_get(settings, "gtk-cursor-theme-name", &cursor_theme,
                         "gtk-cursor-theme-size", &cursor_size, NULL);
            g_message("ReGreet cursor: %s size %d", cursor_theme, cursor_size);
            g_free(cursor_theme);
            arrange(window);
            g_object_unref(window);
            return G_SOURCE_REMOVE;
        }
        g_object_unref(window);
    }
    return G_SOURCE_CONTINUE;
}

__attribute__((constructor)) static void start(void) {
    char executable[4096];
    ssize_t n=readlink("/proc/self/exe", executable, sizeof(executable)-1);
    if (n<0) return;
    executable[n]='\0';
    if (g_str_has_suffix(executable, "/regreet")) g_timeout_add(100, find_window, NULL);
}
