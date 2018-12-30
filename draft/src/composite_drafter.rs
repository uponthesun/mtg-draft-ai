use crate::api::*;
use std::collections::HashMap;
pub struct CompositeDrafter {

}

// Draft brains will make determinations on how to draft based
// on various metrics provided to them within card data.

/* A rudimentary brain that counts mana symbols in mana costs and attempts to find cards
 with average color similar to that of the existing cards in our deck. */
pub struct DraftColorBrain {
}

impl DraftColorBrain {
    // Function that builds a hash map of colors and their weights; higher weights are closer to our
    // current colors.
    // TODO: In the python conversion, this state should be kept and updated incrementally, rather
    // than recalculated wholesale every pick.
    fn calc_preferences(&self, cards_owned: &[Card]) -> HashMap<BasicMana, i32> {
        let mut mana_prefs: HashMap<BasicMana, i32> = HashMap::new();
        for card in cards_owned.iter() {
            for symbol in card.mana_cost.cost.iter() {
                // TODO: Find a good way to return the primitive mana types of complex mana types
                // and increment our hashmap values accordingly.
                match symbol {
                    Mana::XCost(string) => (),
                    Mana::Phyrexian(basic) => {mana_prefs.entry(basic.clone()).and_modify(|m| { *m += 1 }).or_insert(1);},
                    Mana::Split(basic, basic2) => {
                        mana_prefs.entry(basic.clone()).and_modify(|m| { *m += 1 }).or_insert(1);
                        mana_prefs.entry(basic2.clone()).and_modify(|m| { *m += 1 }).or_insert(1);
                    },
                    Mana::Standard(basic) => {mana_prefs.entry(basic.clone()).and_modify(|m| { *m += 2 }).or_insert(2);},
                    Mana::NumGeneric(amt) => (),
                    Mana::SplitGeneric(basic) => {mana_prefs.entry(basic.clone()).and_modify(|m| { *m += 1 }).or_insert(1);},
                }
            }
        }
        mana_prefs
    }

    fn get_card_weight<'a>(&self, card: &'a Card, cards_owned: &[Card],
                           draft_info: &DraftInfo, prefs: &HashMap<BasicMana, i32>) -> (CardWeight){
        let mut weight: i32 = 0;
        for symbol in card.mana_cost.cost.iter() {
            // The mana cost structure sort of breaks down here. In c# I could do this much easier
            // with a lambda, not sure what the right solution is in rust. This match function could
            // also probably be merged with the one used for preference generation as well.
            match symbol {
                Mana::XCost(string) => (),
                Mana::Phyrexian(basic) => match prefs.get(&basic) {
                    Some(val) => weight += val,
                    None => ()
                },
                Mana::Split(basic, basic2) => {
                    match prefs.get(&basic) {
                        Some(val) => weight += val / 2,
                        None => ()
                    };
                    match prefs.get(&basic2) {
                        Some(val) => weight += val / 2,
                        None => ()
                    }
                },
                Mana::Standard(basic) => match prefs.get(&basic) {
                    Some(val) => weight += val,
                    None => ()
                },
                Mana::NumGeneric(amt) => (),
                Mana::SplitGeneric(basic) => match prefs.get(&basic) {
                    Some(val) => weight += val,
                    None => ()
                },
            }
        }
        CardWeight {card: card.clone(), weight: weight}
    }
}

impl DraftBrain for DraftColorBrain{
    // In truth I think this strategy is terrible and will move to clustering for python,
    // but I'm going to write it out as a way to help think through the problem.
    fn get_pack_weights<'a>(&self, pack: &'a [Card], cards_owned: &[Card],
                            draft_info: &DraftInfo) -> Vec<CardWeight> {
        let prefs = self.calc_preferences(cards_owned);
        let mut weights: Vec<CardWeight> = Vec::new();
        for card in cards_owned {
            let m = self.get_card_weight(card, cards_owned, draft_info, &prefs);
            weights.push(m);
        };
        weights
    }
}

#[derive(Debug, Clone, Hash, Eq, PartialEq)]
pub struct CardWeight {
    pub card: Card,
    pub weight: i32
}

pub trait DraftBrain {
    fn get_pack_weights<'a>(&self, pack: &'a [Card], cards_owned: &[Card],
                            draft_info: &DraftInfo) -> Vec<CardWeight>;
}
