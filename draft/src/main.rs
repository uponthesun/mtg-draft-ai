mod random_drafter;
mod api;
use crate::api::Drafter;

fn main() {
    let drafter = random_drafter::RandomDrafter {};

    let pack = vec![api::Card::new("Battle Hymn"), api::Card::new("Earthquake")];
    let cards_owned : Vec<api::Card> = vec![];

    for _i in 1..5 {
        println!("{}", drafter.pick(&pack, &cards_owned));
    }
}