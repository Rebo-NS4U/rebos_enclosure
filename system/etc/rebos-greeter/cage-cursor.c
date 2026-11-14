#define _GNU_SOURCE
#define WLR_USE_UNSTABLE
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <wlr/types/wlr_cursor.h>
#include <wlr/types/wlr_cursor_shape_v1.h>
#include <wlr/types/wlr_seat.h>
#include <wlr/types/wlr_xcursor_manager.h>

/* GTK's Wayland fallback uses built-in cursor images when cursor-shape-v1 is
 * unavailable. Bridge shape requests to Cage's themed cursor, rather than
 * merely changing XCURSOR_THEME, which does not affect those GTK images.
 * Cage has one seat/cursor. Keep this extension scoped to that executable. */
static struct wlr_cursor *greeter_cursor;
static struct wlr_xcursor_manager *greeter_theme;
static int has_shape_manager;
static struct wl_listener shape_request, shape_destroy;

static void destroy_shape(struct wl_listener *listener, void *data) {
    (void)listener; (void)data;
    wl_list_remove(&shape_request.link);
    wl_list_remove(&shape_destroy.link);
    has_shape_manager = 0;
}

static int is_cage(void) {
    char executable[4096];
    ssize_t n = readlink("/proc/self/exe", executable, sizeof(executable) - 1);
    if (n <= 0) return 0;
    executable[n] = '\0';
    const char *base = strrchr(executable, '/');
    return base && strcmp(base, "/cage") == 0;
}

static void request_shape(struct wl_listener *listener, void *data) {
    (void)listener;
    struct wlr_cursor_shape_manager_v1_request_set_shape_event *event = data;
    struct wlr_seat *seat = event->seat_client->seat;
    if (event->device_type != WLR_CURSOR_SHAPE_MANAGER_V1_DEVICE_TYPE_POINTER ||
        seat->pointer_state.focused_client != event->seat_client ||
        !(seat->capabilities & WL_SEAT_CAPABILITY_POINTER) ||
        !wlr_seat_client_validate_event_serial(event->seat_client, event->serial) ||
        !greeter_cursor || !greeter_theme) return;
    const char *name = wlr_cursor_shape_v1_name(event->shape);
    if (name) wlr_cursor_set_xcursor(greeter_cursor, greeter_theme, name);
}

struct wlr_xcursor_manager *wlr_xcursor_manager_create(const char *name, unsigned size) {
    typedef struct wlr_xcursor_manager *(*Create)(const char *, unsigned);
    Create original = (Create)dlsym(RTLD_NEXT, "wlr_xcursor_manager_create");
    if (!original) return NULL;
    if (is_cage()) {
        name = "GoogleDot-Black";
        size = 20;
    }
    struct wlr_xcursor_manager *manager = original(name, size);
    if (is_cage() && !greeter_theme) greeter_theme = manager;
    return manager;
}

struct wlr_cursor *wlr_cursor_create(void) {
    typedef struct wlr_cursor *(*Create)(void);
    Create original = (Create)dlsym(RTLD_NEXT, "wlr_cursor_create");
    struct wlr_cursor *cursor = original ? original() : NULL;
    if (is_cage()) greeter_cursor = cursor;
    return cursor;
}

/* Newer Cage builds implement this protocol themselves. Record that and let
 * their native handler own it, avoiding duplicate protocol globals/listeners. */
struct wlr_cursor_shape_manager_v1 *wlr_cursor_shape_manager_v1_create(
        struct wl_display *display, uint32_t version) {
    typedef struct wlr_cursor_shape_manager_v1 *(*Create)(struct wl_display *, uint32_t);
    Create original = (Create)dlsym(RTLD_NEXT, "wlr_cursor_shape_manager_v1_create");
    struct wlr_cursor_shape_manager_v1 *manager = original ? original(display, version) : NULL;
    if (is_cage() && manager) has_shape_manager = 1;
    return manager;
}

struct wlr_seat *wlr_seat_create(struct wl_display *display, const char *name) {
    typedef struct wlr_seat *(*Create)(struct wl_display *, const char *);
    Create original = (Create)dlsym(RTLD_NEXT, "wlr_seat_create");
    struct wlr_seat *seat = original ? original(display, name) : NULL;
    if (seat && is_cage() && !has_shape_manager) {
        struct wlr_cursor_shape_manager_v1 *manager =
            wlr_cursor_shape_manager_v1_create(display, 1);
        if (manager) {
            shape_request.notify = request_shape;
            wl_signal_add(&manager->events.request_set_shape, &shape_request);
            shape_destroy.notify = destroy_shape;
            wl_signal_add(&manager->events.destroy, &shape_destroy);
            fprintf(stderr, "ReGreet: cursor-shape-v1 bridge enabled for GoogleDot\n");
        }
    }
    return seat;
}
