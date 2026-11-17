// Loaded only by Starwake's launcher. Uses Wayland confinement, not cursor warping.
#include <QGuiApplication>
#include <QtGui/qguiapplication_platform.h>
#include <QQuickWindow>
#include <QQuickItem>
#include <QPointer>
#include <QCursor>
#include <QTimer>
#include <wayland-client.h>
#include "pointer-constraints.h"
#include <cstring>

namespace {
struct Fence {
    wl_display *display = nullptr;
    wl_registry *registry = nullptr;
    zwp_pointer_constraints_v1 *manager = nullptr;
    zwp_confined_pointer_v1 *constraint = nullptr;
    QPointer<QQuickWindow> bound;
    bool initialized = false;
    bool warned = false;
    bool cursorHidden = false;
    void hideCursor() {
        if (cursorHidden) return;
        // Application overrides include tablet tools; MouseArea only covers mouse hover.
        QGuiApplication::setOverrideCursor(QCursor(Qt::BlankCursor));
        cursorHidden = true;
    }
    static void global(void *data, wl_registry *registry, uint32_t name, const char *interface, uint32_t) {
        auto *self = static_cast<Fence *>(data);
        if (!std::strcmp(interface, zwp_pointer_constraints_v1_interface.name))
            self->manager = static_cast<zwp_pointer_constraints_v1 *>(wl_registry_bind(registry,name,&zwp_pointer_constraints_v1_interface,1));
    }
    static void removed(void *, wl_registry *, uint32_t) {}
    static void confined(void *data, zwp_confined_pointer_v1 *) {
        auto *self = static_cast<Fence *>(data);
        if (self->bound) self->bound->contentItem()->setProperty("starwakeConfined",true);
        qInfo("Starwake pointer confined");
    }
    static void unconfined(void *data, zwp_confined_pointer_v1 *) {
        auto *self = static_cast<Fence *>(data);
        if (self->bound) self->bound->contentItem()->setProperty("starwakeConfined",false);
    }
    void release() {
        if (cursorHidden) {
            QGuiApplication::restoreOverrideCursor();
            cursorHidden = false;
        }
        if (constraint) {
            zwp_confined_pointer_v1_destroy(constraint); constraint = nullptr;
            if (bound) bound->contentItem()->setProperty("starwakeConfined",false);
            qInfo("Starwake pointer released");
            wl_display_flush(display);
        }
        bound = nullptr;
    }
    static QQuickItem *findArena(QQuickItem *item) {
        if (item->objectName() == "starwakeArena") return item;
        for (auto *child : item->childItems()) if (auto *found = findArena(child)) return found;
        return nullptr;
    }
    void tick() {
        QQuickWindow *game = nullptr;
        QQuickItem *arena = nullptr;
        for (auto *window : QGuiApplication::allWindows()) {
            auto *quick = qobject_cast<QQuickWindow *>(window);
            if (quick && (arena = findArena(quick->contentItem()))) { game = quick; break; }
        }
        if (!game || !arena->property("capturePointer").toBool() || !game->isActive() || !game->isVisible()) { release(); return; }
        if (constraint && bound != game) release();
        hideCursor();
        if (constraint && bound == game) return;
        auto *native = qGuiApp->nativeInterface<QNativeInterface::QWaylandApplication>();
        if (!native) return;
        if (!initialized) {
            initialized = true; display = native->display(); registry = wl_display_get_registry(display);
            static const wl_registry_listener listener{global,removed};
            wl_registry_add_listener(registry,&listener,this);
            wl_display_roundtrip(display);
        }
        if (!manager || !native->pointer()) {
            if (!warned) { qWarning("Starwake: compositor pointer confinement unavailable"); warned = true; }
            return;
        }
        // Qt 6.9+ Wayland WId is the wl_surface, not an integer window number.
        auto *surface = reinterpret_cast<wl_surface *>(game->winId());
        auto *region = wl_compositor_create_region(native->compositor());
        wl_region_add(region,0,0,qMax(1,game->width()),qMax(1,game->height()));
        bound = game;
        constraint = zwp_pointer_constraints_v1_confine_pointer(manager,surface,native->pointer(),region,ZWP_POINTER_CONSTRAINTS_V1_LIFETIME_PERSISTENT);
        wl_region_destroy(region);
        static const zwp_confined_pointer_v1_listener listener{confined,unconfined};
        zwp_confined_pointer_v1_add_listener(constraint,&listener,this);
        wl_display_flush(display);
    }
    ~Fence() { release(); if(manager) zwp_pointer_constraints_v1_destroy(manager); if(registry) wl_registry_destroy(registry); }
};
void start() {
    qInfo("Starwake pointer confinement initialized");
    auto *fence = new Fence;
    auto *timer = new QTimer(qApp);
    QObject::connect(timer,&QTimer::timeout,qApp,[fence]{fence->tick();});
    QObject::connect(qApp,&QCoreApplication::aboutToQuit,qApp,[fence,timer]{timer->stop();delete fence;});
    timer->start(16);
}
Q_COREAPP_STARTUP_FUNCTION(start)
}
