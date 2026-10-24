//! Physical outer-window geometry and a monotonic, coalescing persistence queue.
//! These helpers do not touch the filesystem, window system or personal data.
use serde::{Deserialize, Serialize};
use std::time::Duration;

pub const GEOMETRY_DELAY: Duration = Duration::from_millis(900);

#[derive(Serialize, Deserialize, Clone, Copy, Debug, PartialEq, Eq)]
pub struct Geometry {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

#[derive(Clone, Copy, Debug)]
pub struct WorkArea {
    pub x: i32,
    pub y: i32,
    pub width: u32,
    pub height: u32,
}

impl WorkArea {
    fn right(self) -> i64 { i64::from(self.x) + i64::from(self.width) }
    fn bottom(self) -> i64 { i64::from(self.y) + i64::from(self.height) }
    fn overlap(self, geometry: Geometry) -> i64 {
        let width = (self.right().min(i64::from(geometry.x) + i64::from(geometry.width))
            - i64::from(self.x).max(i64::from(geometry.x))).max(0);
        let height = (self.bottom().min(i64::from(geometry.y) + i64::from(geometry.height))
            - i64::from(self.y).max(i64::from(geometry.y))).max(0);
        width * height
    }
    fn distance(self, geometry: Geometry) -> f64 {
        let x = f64::from(geometry.x) + f64::from(geometry.width) / 2.;
        let y = f64::from(geometry.y) + f64::from(geometry.height) / 2.;
        let dx = (f64::from(self.x) - x).max(0.).max(x - self.right() as f64);
        let dy = (f64::from(self.y) - y).max(0.).max(y - self.bottom() as f64);
        dx * dx + dy * dy
    }
}

/// Prefer the display containing most of the saved box. If a display has gone,
/// use the nearest remaining work area and clamp the entire outer frame into it.
pub fn visible_geometry(geometry: Geometry, areas: &[WorkArea]) -> Option<Geometry> {
    if geometry.width == 0 || geometry.height == 0 { return None; }
    let area = areas.iter().filter(|area| area.width > 0 && area.height > 0).max_by(|a, b| {
        a.overlap(geometry).cmp(&b.overlap(geometry))
            .then_with(|| b.distance(geometry).total_cmp(&a.distance(geometry)))
    })?;
    let width = geometry.width.min(area.width);
    let height = geometry.height.min(area.height);
    Some(Geometry {
        x: i64::from(geometry.x).clamp(i64::from(area.x), area.right() - i64::from(width)) as i32,
        y: i64::from(geometry.y).clamp(i64::from(area.y), area.bottom() - i64::from(height)) as i32,
        width,
        height,
    })
}

/// Tauri's set_size consumes an inner size. Subtract the decoration measured on
/// the target monitor, keeping both this result and the saved frame physical.
pub fn client_size_for_outer(wanted: Geometry, outer: (u32, u32), inner: (u32, u32)) -> (u32, u32) {
    (wanted.width.saturating_sub(outer.0.saturating_sub(inner.0)).max(1),
     wanted.height.saturating_sub(outer.1.saturating_sub(inner.1)).max(1))
}

/// The tray sends physical coordinates. Choose the monitor from that point,
/// then keep the entire scaled menu clear of its taskbar and work-area edges.
pub fn tray_menu_geometry(x: f64, y: f64, scale: f64, areas: &[WorkArea]) -> Option<Geometry> {
    if !x.is_finite() || !y.is_finite() || !scale.is_finite() || scale <= 0. { return None; }
    let cursor = Geometry { x: x.round() as i32, y: y.round() as i32, width: 1, height: 1 };
    let area = areas.iter().filter(|area| area.width > 0 && area.height > 0).max_by(|a, b| {
        a.overlap(cursor).cmp(&b.overlap(cursor)).then_with(|| b.distance(cursor).total_cmp(&a.distance(cursor)))
    })?;
    let margin = (8. * scale).round() as u32;
    let width = ((312. * scale).round() as u32).min(area.width.saturating_sub(margin * 2).max(1));
    let height = ((374. * scale).round() as u32).min(area.height.saturating_sub(margin * 2).max(1));
    let inset_x = margin.min((area.width - width) / 2);
    let inset_y = margin.min((area.height - height) / 2);
    Some(Geometry {
        x: (i64::from(cursor.x) - i64::from(width) + i64::from(margin)).clamp(
            i64::from(area.x) + i64::from(inset_x), area.right() - i64::from(width) - i64::from(inset_x)) as i32,
        y: (i64::from(cursor.y) - i64::from(height) - i64::from(margin)).clamp(
            i64::from(area.y) + i64::from(inset_y), area.bottom() - i64::from(height) - i64::from(inset_y)) as i32,
        width, height,
    })
}

#[derive(Default)]
pub struct GeometryQueue {
    latest: Option<Geometry>,
    changed_at: Duration,
    revision: u64,
    written: u64,
    worker_running: bool,
}

impl GeometryQueue {
    /// Return true only when this burst needs its one persistence worker.
    pub fn record(&mut self, geometry: Geometry, now: Duration) -> bool {
        if self.latest == Some(geometry) { return false; }
        self.latest = Some(geometry);
        self.changed_at = now;
        self.revision += 1;
        if self.worker_running { return false; }
        self.worker_running = true;
        true
    }
    pub fn next_wait(&mut self, now: Duration) -> Option<Duration> {
        if self.latest.is_none() || self.revision == self.written {
            self.worker_running = false;
            return None;
        }
        Some(GEOMETRY_DELAY.saturating_sub(now.saturating_sub(self.changed_at)))
    }
    pub fn candidate(&self, now: Duration, force: bool) -> Option<(u64, Geometry)> {
        if self.revision == self.written || (!force && now.saturating_sub(self.changed_at) < GEOMETRY_DELAY) {
            return None;
        }
        self.latest.map(|geometry| (self.revision, geometry))
    }
    /// A move received during an older write must remain pending.
    pub fn acknowledge(&mut self, revision: u64) { self.written = self.written.max(revision); }
}

#[cfg(test)]
mod tests {
    use super::*;
    fn area(x: i32, y: i32, width: u32, height: u32) -> WorkArea { WorkArea { x, y, width, height } }
    fn box_at(x: i32, y: i32, width: u32, height: u32) -> Geometry { Geometry { x, y, width, height } }

    #[test]
    fn a_one_pixel_overlap_restores_the_whole_frame_and_title_bar() {
        let work = area(0, 0, 1920, 1040);
        let restored = visible_geometry(box_at(1919, 100, 1000, 700), &[work]).unwrap();
        assert_eq!(restored, box_at(920, 100, 1000, 700));
        assert_eq!(visible_geometry(box_at(100, -699, 1000, 700), &[work]).unwrap().y, 0);
    }
    #[test]
    fn a_removed_display_uses_the_nearest_work_area_without_recentering() {
        let displays = [area(-1920, 0, 1920, 1040), area(0, 0, 1920, 1040)];
        assert_eq!(visible_geometry(box_at(2800, 180, 900, 650), &displays).unwrap(),
            box_at(1020, 180, 900, 650));
    }
    #[test]
    fn negative_monitor_coordinates_and_largest_overlap_are_preserved() {
        let displays = [area(-1920, -200, 1920, 1080), area(0, 0, 1920, 1040)];
        let saved = box_at(-1800, -100, 900, 650);
        assert_eq!(visible_geometry(saved, &displays), Some(saved));
        assert_eq!(visible_geometry(box_at(-700, 50, 900, 650), &displays).unwrap().x, -900);
    }
    #[test]
    fn oversized_or_corrupt_boxes_fit_the_work_area_without_integer_overflow() {
        assert_eq!(visible_geometry(box_at(i32::MAX, i32::MIN, u32::MAX, u32::MAX), &[area(0, 40, 683, 344)]),
            Some(box_at(0, 40, 683, 344)));
        assert_eq!(visible_geometry(box_at(0, 0, 0, 10), &[area(0, 0, 100, 100)]), None);
        assert_eq!(visible_geometry(box_at(0, 0, 10, 10), &[]), None);
    }
    #[test]
    fn physical_outer_frames_round_trip_at_100_and_150_percent() {
        for (outer, inner) in [((1000, 700), (984, 661)), ((1500, 1050), (1476, 991))] {
            let saved = box_at(120, 80, outer.0, outer.1);
            assert_eq!(client_size_for_outer(saved, outer, inner), inner);
            assert_eq!(visible_geometry(saved, &[area(0, 0, 2400, 1600)]), Some(saved));
        }
        assert_eq!(client_size_for_outer(box_at(0, 0, 1000, 700), (1500, 1050), (1476, 991)), (976, 641));
    }
    #[test]
    fn tray_menu_stays_in_the_requested_monitor_at_both_dpi_scales() {
        let displays = [area(-1920, -200, 1920, 1040), area(0, 40, 2400, 1520)];
        for (x, y, scale, target) in [(-50., 850., 1., displays[0]), (2390., 1580., 1.5, displays[1]),
            (2., 0., 1., displays[1]), (-1925., 0., 1.5, displays[0])] {
            let menu = tray_menu_geometry(x, y, scale, &displays).unwrap();
            assert!(menu.x >= target.x && menu.y >= target.y);
            assert!(i64::from(menu.x) + i64::from(menu.width) <= target.right());
            assert!(i64::from(menu.y) + i64::from(menu.height) <= target.bottom());
            assert_eq!(menu.width, (312. * scale).round() as u32);
        }
        let tiny = tray_menu_geometry(300., 190., 1.5, &[area(0, 40, 320, 160)]).unwrap();
        assert!(tiny.width <= 320 && tiny.height <= 160);
        assert!(tray_menu_geometry(f64::NAN, 0., 1., &displays).is_none());
    }
    #[test]
    fn a_drag_coalesces_changing_events_and_closing_flushes_the_latest_box() {
        let mut queue = GeometryQueue::default();
        let mut workers = 0;
        for tick in 0..300 {
            workers += usize::from(queue.record(box_at(tick, 50, 900, 650), Duration::from_millis(tick as u64 * 2)));
            assert!(queue.candidate(Duration::from_millis(tick as u64 * 2), false).is_none());
        }
        assert_eq!(workers, 1);
        let (revision, latest) = queue.candidate(Duration::from_millis(600), true).unwrap();
        assert_eq!(latest.x, 299);
        queue.acknowledge(revision);
        assert!(queue.next_wait(Duration::from_secs(2)).is_none());
    }
    #[test]
    fn a_quiet_period_writes_once_and_a_move_during_writing_is_not_lost() {
        let mut queue = GeometryQueue::default();
        queue.record(box_at(1, 1, 900, 650), Duration::ZERO);
        let first = queue.candidate(GEOMETRY_DELAY, false).unwrap();
        queue.record(box_at(2, 1, 900, 650), GEOMETRY_DELAY);
        queue.acknowledge(first.0);
        assert!(queue.candidate(GEOMETRY_DELAY, false).is_none());
        let next = queue.candidate(GEOMETRY_DELAY * 2, false).unwrap();
        assert_eq!(next.1.x, 2);
        queue.acknowledge(next.0);
        assert!(queue.next_wait(GEOMETRY_DELAY * 3).is_none());
        assert!(queue.record(box_at(3, 1, 900, 650), GEOMETRY_DELAY * 3));
    }
}
