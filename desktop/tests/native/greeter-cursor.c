/* Exercise the real bridge with wlroots seats/serials, without a desktop. */
#include <assert.h>
#include <stdint.h>
#include <sys/socket.h>
#include <stdlib.h>
#include "../../../system/etc/rebos-greeter/cage-cursor.c"

static int updates;
static const char *last_shape;
void wlr_cursor_set_xcursor(struct wlr_cursor *cursor,
        struct wlr_xcursor_manager *theme, const char *name) {
    assert(cursor == greeter_cursor && theme == greeter_theme);
    assert(wlr_xcursor_manager_get_xcursor(theme, name, 1));
    last_shape = name;
    updates++;
}

int main(int argc, char **argv) {
    (void)argv;
    assert(is_cage());
    struct wl_display *display = wl_display_create();
    if (argc > 1) {
        /* A newer Cage owns its native protocol handler. */
        assert(wlr_cursor_shape_manager_v1_create(display, 2));
        assert(wlr_seat_create(display, "native"));
        assert(has_shape_manager && !shape_request.notify);
        wl_display_destroy(display);
        puts("Native Cage cursor-shape support is preserved");
        return 0;
    }
    struct wlr_seat *seat = wlr_seat_create(display, "test");
    assert(seat && has_shape_manager && shape_request.notify);
    greeter_theme = wlr_xcursor_manager_create(NULL, 24);
    assert(greeter_theme && strcmp(greeter_theme->name, "GoogleDot-Black") == 0);
    assert(wlr_xcursor_manager_load(greeter_theme, 1));
    greeter_cursor = (struct wlr_cursor *)(uintptr_t)1;
    int sockets[2];
    assert(socketpair(AF_UNIX, SOCK_STREAM, 0, sockets) == 0);
    struct wl_client *wl_client = wl_client_create(display, sockets[0]);
    assert(wl_client);
    struct wlr_seat_client client = {.seat = seat, .client = wl_client};
    seat->pointer_state.focused_client = &client;
    seat->capabilities = WL_SEAT_CAPABILITY_POINTER;
    struct wlr_cursor_shape_manager_v1_request_set_shape_event event = {
        .seat_client = &client,
        .device_type = WLR_CURSOR_SHAPE_MANAGER_V1_DEVICE_TYPE_POINTER,
        .serial = wlr_seat_client_next_serial(&client),
        .shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_DEFAULT,
    };
    request_shape(NULL, &event);
    assert(updates == 1 && strcmp(last_shape, "default") == 0);
    event.shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_TEXT;
    request_shape(NULL, &event);
    assert(updates == 2 && strcmp(last_shape, "text") == 0);
    event.shape = WP_CURSOR_SHAPE_DEVICE_V1_SHAPE_POINTER;
    request_shape(NULL, &event);
    assert(updates == 3 && strcmp(last_shape, "pointer") == 0);
    seat->pointer_state.focused_client = NULL;
    request_shape(NULL, &event);
    seat->pointer_state.focused_client = &client;
    event.serial += 100;
    request_shape(NULL, &event);
    event.serial = wlr_seat_client_next_serial(&client);
    event.device_type = WLR_CURSOR_SHAPE_MANAGER_V1_DEVICE_TYPE_TABLET_TOOL;
    request_shape(NULL, &event);
    event.device_type = WLR_CURSOR_SHAPE_MANAGER_V1_DEVICE_TYPE_POINTER;
    seat->capabilities = 0;
    request_shape(NULL, &event);
    assert(updates == 3);
    seat->pointer_state.focused_client = NULL;
    wlr_xcursor_manager_destroy(greeter_theme);
    wl_display_destroy_clients(display);
    close(sockets[1]);
    wl_display_destroy(display);
    puts("GoogleDot default/text/pointer requests and focus/serial checks passed");
    return 0;
}
