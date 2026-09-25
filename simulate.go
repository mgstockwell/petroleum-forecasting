package main

import (
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log"
	"math"
	"math/rand"
	"os"
	"strconv"
	"sync"
	"time"
)

type MacroParams struct {
	S0               float64 `json:"s0"`
	SigmaCrude       float64 `json:"sigma_crude"`
	JumpLambda       float64 `json:"jump_lambda"`
	JumpMu           float64 `json:"jump_mu"`
	CrackGas0        float64 `json:"crack_gas_0"`
	CrackDiesel0     float64 `json:"crack_diesel_0"`
	SigmaCrackGas    float64 `json:"sigma_crack_gas"`
	SigmaCrackDiesel float64 `json:"sigma_crack_diesel"`
	DayOfYear        int     `json:"day_of_year"`
	Freight0         float64 `json:"freight_0"`
	ChokepointLambda float64 `json:"chokepoint_lambda"`
	ChokepointJumpMu float64 `json:"chokepoint_jump_mu"`
	SprTrigger       float64 `json:"spr_trigger_price"`
	SprFloor         float64 `json:"spr_floor_price"`
	SprMaxDraw       float64 `json:"spr_max_draw_mbpd"`
	SaudiProd        float64 `json:"saudi_prod"`
	SaudiCap         float64 `json:"saudi_cap"`
	RussiaProd       float64 `json:"russia_prod"`
	RussiaDecay      float64 `json:"russia_decay"`
	IranProd         float64 `json:"iran_prod"`
	IranCap          float64 `json:"iran_cap"`
	UsProd           float64 `json:"us_prod"`
	UsCap            float64 `json:"us_cap"`
	OtherProd        float64 `json:"other_prod"`
	OtherCap         float64 `json:"other_cap"`
	HormuzRate       float64 `json:"hormuz_rate"`
	BabRate          float64 `json:"bab_rate"`
	ShippingCost0    float64 `json:"shipping_cost_0"`
	Sims             int     `json:"sims"`
}

const (
	Days             = 180
	DefaultSims      = 2000
	Dt               = 1.0 / 365.0
	TaxG             = 0.57
	DistG            = 0.65
	TaxD             = 0.65
	DistD            = 0.85
	ChokeRefRateMbpd = 20.0 // Hormuz baseline; disruption severity scales relative to this
)

func main() {
	rand.Seed(time.Now().UnixNano())

	macroFile, err := os.Open("params_macro.json")
	if err != nil {
		legacyFile, legacyErr := os.Open("params.json")
		if legacyErr != nil {
			log.Fatalf("failed to open params_macro.json or params.json: %v / %v", err, legacyErr)
		}
		defer legacyFile.Close()
		var legacy MacroParams
		if err := json.NewDecoder(legacyFile).Decode(&legacy); err != nil {
			log.Fatalf("failed to decode legacy params.json: %v", err)
		}
		legacyDay := time.Now().Day()
		legacy.DayOfYear = legacyDay
		runSimulation(legacy)
		return
	}
	defer macroFile.Close()

	var p MacroParams
	if err := json.NewDecoder(macroFile).Decode(&p); err != nil {
		log.Fatalf("failed to decode params_macro.json: %v", err)
	}
	if p.DayOfYear == 0 {
		p.DayOfYear = time.Now().YearDay()
	}

	runSimulation(p)
}

func runSimulation(p MacroParams) {
	sims := p.Sims
	if sims <= 0 {
		sims = DefaultSims
	}

	var wg sync.WaitGroup
	gasResults := make([][]string, sims)
	dieselResults := make([][]string, sims)

	fmt.Printf("Running %d multi-factor macro paths...\n", sims)
	for i := 0; i < sims; i++ {
		wg.Add(1)
		go func(idx int) {
			defer wg.Done()
			st := p.S0
			cGas := p.CrackGas0
			cDies := p.CrackDiesel0
			freight := p.Freight0
			shippingCost := p.ShippingCost0
			saudiQ := p.SaudiProd
			russiaQ := p.RussiaProd
			usQ := p.UsProd
			iranQ := p.IranProd
			otherQ := p.OtherProd

			gasPath := make([]string, Days)
			dieselPath := make([]string, Days)

			for t := 0; t < Days; t++ {
				russiaQ -= russiaQ * p.RussiaDecay * Dt
				saudiQ += 0.05 * (80.0 - st) * Dt
				if saudiQ > p.SaudiCap {
					saudiQ = p.SaudiCap
				}
				if saudiQ < 7.0 {
					saudiQ = 7.0
				}

				usQ += 0.06 * (st - 65.0) * Dt // shale ramps above breakeven, unlike Saudi's inverse response
				if usQ > p.UsCap {
					usQ = p.UsCap
				}
				if usQ < 11.0 { // higher marginal-cost floor than Saudi spare capacity
					usQ = 11.0
				}

				iranQ += 0.01 * (p.IranCap - iranQ) * Dt // sanctions: slow drift to cap, no price response
				if iranQ > p.IranCap {
					iranQ = p.IranCap
				}
				if iranQ < 2.5 {
					iranQ = 2.5
				}

				otherQ += 0.02 * (75.0 - st) * Dt
				if otherQ > p.OtherCap {
					otherQ = p.OtherCap
				}
				if otherQ < 0.9*p.OtherProd {
					otherQ = 0.9 * p.OtherProd
				}

				sprFlow := 0.0
				if st > p.SprTrigger {
					sprFlow = p.SprMaxDraw
				} else if st < p.SprFloor {
					sprFlow = -0.1
				}

				freightJump := 0.0
				shippingJump := 0.0
				supplyShock := 0.0
				if rand.Float64() < (p.ChokepointLambda * Dt) {
					severity := 1.0
					totalChoke := p.HormuzRate + p.BabRate
					if totalChoke > 0 {
						chokeRate := p.BabRate
						if rand.Float64() < p.HormuzRate/totalChoke {
							chokeRate = p.HormuzRate
						}
						severity = chokeRate / ChokeRefRateMbpd
					}
					baseJump := math.Abs(rand.NormFloat64()*2.0 + p.ChokepointJumpMu)
					freightJump = baseJump * severity
					shippingJump = baseJump * severity * 0.5
					supplyShock = 0.05 * severity * ChokeRefRateMbpd
				}
				freight += 5.0*(p.Freight0-freight)*Dt + freightJump
				shippingCost += 8.0*(p.ShippingCost0-shippingCost)*Dt + shippingJump

				currentDay := float64((p.DayOfYear + t) % 365)
				seasonalGas := 5.0 * math.Sin((2.0*math.Pi/365.0)*currentDay-1.5)
				seasonalDiesel := 3.0 * math.Sin((2.0*math.Pi/365.0)*currentDay+0.8)
				cGas += seasonalGas*Dt + rand.NormFloat64()*1.2
				cDies += seasonalDiesel*Dt + rand.NormFloat64()*1.0

				supplyImbalance := (saudiQ + russiaQ + usQ + iranQ + otherQ + sprFlow - supplyShock) -
					(p.SaudiProd + p.RussiaProd + p.UsProd + p.IranProd + p.OtherProd)
				mu := -0.1 * supplyImbalance
				dS := mu*st*Dt + p.SigmaCrude*st*math.Sqrt(Dt)*rand.NormFloat64()
				st += dS
				st = math.Max(st, 0.01)

				gasPrice := (st / 42.0) + (cGas / 42.0) + (freight / 42.0) + (shippingCost / 42.0) + TaxG + DistG
				dieselPrice := (st / 42.0) + (cDies / 42.0) + (freight / 42.0) + (shippingCost / 42.0) + TaxD + DistD
				gasPath[t] = strconv.FormatFloat(gasPrice, 'f', 2, 64)
				dieselPath[t] = strconv.FormatFloat(dieselPrice, 'f', 2, 64)
			}

			gasResults[idx] = gasPath
			dieselResults[idx] = dieselPath
		}(i)
	}
	wg.Wait()

	if err := writeCSV("results_macro_gas.csv", gasResults); err != nil {
		log.Fatalf("failed to write macro gas results: %v", err)
	}
	if err := writeCSV("results_macro_diesel.csv", dieselResults); err != nil {
		log.Fatalf("failed to write macro diesel results: %v", err)
	}
	if err := writeCSV("results_gas.csv", gasResults); err != nil {
		log.Fatalf("failed to write gas results: %v", err)
	}
	if err := writeCSV("results_diesel.csv", dieselResults); err != nil {
		log.Fatalf("failed to write diesel results: %v", err)
	}
	fmt.Println("Simulation complete. Output saved to macro and legacy CSVs.")
}

func writeCSV(filename string, data [][]string) error {
	file, err := os.Create(filename)
	if err != nil {
		return err
	}
	defer file.Close()
	writer := csv.NewWriter(file)
	defer writer.Flush()
	writer.WriteAll(data)
	return writer.Error()
}
