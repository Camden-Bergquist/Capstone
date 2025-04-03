use crate::{Board, Placement};
use crate::Row; // Needed for generic Board type

/// Applies each placement to a cloned board and returns a list of resulting boards.
pub fn apply_placements<R: Row>(
    board: &Board<R>,
    placements: &[Placement],
) -> Vec<Board<R>> {
    let mut result_boards = Vec::with_capacity(placements.len());

    for placement in placements {
        let mut new_board = board.clone();
        new_board.lock_piece(&placement.location); // lock the piece in place
        result_boards.push(new_board);
    }

    result_boards
}
