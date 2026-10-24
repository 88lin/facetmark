//! A consumed kill handle is not proof of process exit. Retry waits for the
//! shell's Terminated event before a new generation can acquire the library.
use std::sync::{atomic::{AtomicBool, Ordering}, Condvar, Mutex};
use std::time::{Duration, Instant};

#[derive(Clone, Copy, Default, PartialEq, Debug)]
enum Phase { #[default] Idle, Running, Stopping }
#[derive(Default)]
struct Session { generation: u64, phase: Phase }
#[derive(Default)]
pub struct SidecarGate { session: Mutex<Session>, changed: Condvar }
#[derive(Debug, PartialEq)]
pub enum RetryError { Running, ExitUnconfirmed, Exiting }

impl SidecarGate {
    pub fn begin(&self) -> Option<u64> {
        let mut session = self.session.lock().unwrap();
        if session.phase != Phase::Idle { return None; }
        session.generation += 1;
        session.phase = Phase::Running;
        Some(session.generation)
    }
    pub fn is_current(&self, generation: u64) -> bool {
        let session = self.session.lock().unwrap();
        session.generation == generation && session.phase != Phase::Idle
    }
    pub fn stop(&self, generation: u64) -> bool {
        let mut session = self.session.lock().unwrap();
        if session.generation != generation || session.phase != Phase::Running { return false; }
        session.phase = Phase::Stopping;
        true
    }
    pub fn terminated(&self, generation: u64) -> bool {
        let mut session = self.session.lock().unwrap();
        if session.generation != generation || session.phase == Phase::Idle { return false; }
        session.phase = Phase::Idle;
        self.changed.notify_all();
        true
    }
    pub fn wake(&self) {
        let _session = self.session.lock().unwrap();
        self.changed.notify_all();
    }
    pub fn wait_for_retry(&self, timeout: Duration, exiting: &AtomicBool) -> Result<(), RetryError> {
        let deadline = Instant::now() + timeout;
        let mut session = self.session.lock().unwrap();
        loop {
            if exiting.load(Ordering::SeqCst) { return Err(RetryError::Exiting); }
            match session.phase {
                Phase::Idle => return Ok(()),
                Phase::Running => return Err(RetryError::Running),
                Phase::Stopping => {
                    let remaining = deadline.saturating_duration_since(Instant::now());
                    if remaining.is_zero() { return Err(RetryError::ExitUnconfirmed); }
                    session = self.changed.wait_timeout(session, remaining).unwrap().0;
                },
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{mpsc, Arc};

    #[test]
    fn consumed_child_does_not_release_retry_until_terminated() {
        let gate = Arc::new(SidecarGate::default());
        let generation = gate.begin().unwrap();
        let mut child = Some(42);
        assert!(gate.stop(generation));
        assert_eq!(child.take(), Some(42));
        // Negative control: the old child.is_none() check permits a second
        // launch while the old process can still own .desktop.lock.
        assert!(child.is_none());
        assert!(gate.begin().is_none());
        let waiter = gate.clone();
        let (tx, rx) = mpsc::channel();
        let worker = std::thread::spawn(move || {
            tx.send(waiter.wait_for_retry(Duration::from_secs(2), &AtomicBool::new(false))).unwrap();
        });
        assert!(rx.recv_timeout(Duration::from_millis(30)).is_err());
        assert!(!gate.terminated(generation + 1));
        assert!(rx.recv_timeout(Duration::from_millis(30)).is_err());
        assert!(gate.terminated(generation));
        assert_eq!(rx.recv_timeout(Duration::from_secs(1)).unwrap(), Ok(()));
        worker.join().unwrap();
        assert!(gate.begin().unwrap() > generation);
    }

    #[test]
    fn stale_exit_cannot_unlock_a_new_generation_and_timeout_stays_closed() {
        let gate = SidecarGate::default();
        let old = gate.begin().unwrap();
        assert!(gate.terminated(old));
        let current = gate.begin().unwrap();
        assert!(!gate.terminated(old));
        assert!(gate.is_current(current));
        assert_eq!(gate.wait_for_retry(Duration::ZERO, &AtomicBool::new(false)), Err(RetryError::Running));
        assert!(gate.stop(current));
        assert_eq!(gate.wait_for_retry(Duration::from_millis(1), &AtomicBool::new(false)), Err(RetryError::ExitUnconfirmed));
        assert!(gate.begin().is_none());
        assert_eq!(gate.wait_for_retry(Duration::ZERO, &AtomicBool::new(true)), Err(RetryError::Exiting));
    }
}
