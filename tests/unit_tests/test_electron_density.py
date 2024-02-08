import numpy as np
import pandas as pd

from spaxelsleuth.utils.linefns import compute_electron_density, get_n_e_Proxauf2014, get_n_e_Sanders2016


def test_compute_electron_density():

    #//////////////////////////////////////////////////////
    # Test set 1: Proxauf+2014 [SII]-based measurements 

    # Test case 1: valid input 
    R = 1.0
    n_e_truth = 449.3936099807812
    n_e, lolim_mask, uplim_mask = get_n_e_Proxauf2014(np.array([R, R, R]))
    assert np.all(np.isclose(n_e, n_e_truth))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 2: upper/lower limit saturation
    n_e, lolim_mask, uplim_mask = get_n_e_Proxauf2014(np.array([0.1, -0.2, 0.3]))
    assert np.all(n_e == 1e4)
    assert not any(lolim_mask)
    assert all(uplim_mask)

    # Lower limit 
    n_e, lolim_mask, uplim_mask = get_n_e_Proxauf2014(np.array([1.6, 2.0, 999]))
    assert np.all(n_e == 40)
    assert all(lolim_mask)
    assert not any(uplim_mask)

    # Test case 3: NaNs
    n_e, lolim_mask, uplim_mask = get_n_e_Proxauf2014(np.array([np.nan, np.nan, np.nan]))
    assert all(np.isnan(n_e))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 3: infs
    n_e, lolim_mask, uplim_mask = get_n_e_Proxauf2014(np.array([np.inf, np.inf, np.inf]))
    assert all(np.isnan(n_e))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 4: test inside DataFrame 
    df = pd.DataFrame({
        "[SII] ratio (component 1)": [np.nan, np.nan, 0.1, -0.2, 0.3, 1.6, 2.0, 999, 1.0],
    })
    df_updated = compute_electron_density(df=df, ratio="[SII]", diagnostic="Proxauf2014", s=" (component 1)")
    assert np.isnan(df_updated.loc[0, f"n_e (Proxauf2014 ([SII])) (component 1)"])
    assert np.isnan(df_updated.loc[1, f"n_e (Proxauf2014 ([SII])) (component 1)"])
    assert df_updated.loc[2, f"n_e (Proxauf2014 ([SII])) (component 1)"] == 1e4
    assert df_updated.loc[3, f"n_e (Proxauf2014 ([SII])) (component 1)"] == 1e4
    assert df_updated.loc[4, f"n_e (Proxauf2014 ([SII])) (component 1)"] == 1e4
    assert df_updated.loc[5, f"n_e (Proxauf2014 ([SII])) (component 1)"] == 40
    assert df_updated.loc[6, f"n_e (Proxauf2014 ([SII])) (component 1)"] == 40
    assert df_updated.loc[7, f"n_e (Proxauf2014 ([SII])) (component 1)"] == 40
    assert df_updated.loc[8, f"n_e (Proxauf2014 ([SII])) (component 1)"] == n_e_truth

    # Test case 5: test w/o suffix
    df = pd.DataFrame({
        "[SII] ratio": [np.nan, np.nan, 0.1, -0.2, 0.3, 1.6, 2.0, 999, 1.0],
    })
    df_updated = compute_electron_density(df=df, ratio="[SII]", diagnostic="Proxauf2014")
    assert np.isnan(df_updated.loc[0, f"n_e (Proxauf2014 ([SII]))"])
    assert np.isnan(df_updated.loc[1, f"n_e (Proxauf2014 ([SII]))"])
    assert df_updated.loc[2, f"n_e (Proxauf2014 ([SII]))"] == 1e4
    assert df_updated.loc[3, f"n_e (Proxauf2014 ([SII]))"] == 1e4
    assert df_updated.loc[4, f"n_e (Proxauf2014 ([SII]))"] == 1e4
    assert df_updated.loc[5, f"n_e (Proxauf2014 ([SII]))"] == 40
    assert df_updated.loc[6, f"n_e (Proxauf2014 ([SII]))"] == 40
    assert df_updated.loc[7, f"n_e (Proxauf2014 ([SII]))"] == 40
    assert df_updated.loc[8, f"n_e (Proxauf2014 ([SII]))"] == n_e_truth


    #//////////////////////////////////////////////////////
    # Test set 2: Sanders [OII]-based measurements 
    # Test case 1: valid input 
    R = 1.0
    n_e_truth = 469.2290897415315
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[OII]", R=np.array([R, R, R]))
    assert np.all(np.isclose(n_e, n_e_truth))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 2: upper/lower limit saturation
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[OII]", R=np.array([0.1, -0.2, 0.38]))
    assert np.all(n_e == 1e5)
    assert not any(lolim_mask)
    assert all(uplim_mask)

    # Lower limit 
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[OII]", R=np.array([1.46, 2.0, 999]))
    assert np.all(n_e == 1)
    assert all(lolim_mask)
    assert not any(uplim_mask)

    # Test case 3: NaNs
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[OII]", R=np.array([np.nan, np.nan, np.nan]))
    assert all(np.isnan(n_e))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 3: infs
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[OII]", R=np.array([np.inf, np.inf, np.inf]))
    assert all(np.isnan(n_e))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 4: test inside DataFrame 
    df = pd.DataFrame({
        "[OII] ratio (component 1)": [np.nan, np.nan, 0.1, -0.2, 0.3, 1.6, 2.0, 999, 1.0],
    })
    df_updated = compute_electron_density(df=df, ratio="[OII]", diagnostic="Sanders2016", s=" (component 1)")
    assert np.isnan(df_updated.loc[0, f"n_e (Sanders2016 ([OII])) (component 1)"])
    assert np.isnan(df_updated.loc[1, f"n_e (Sanders2016 ([OII])) (component 1)"])
    assert df_updated.loc[2, f"n_e (Sanders2016 ([OII])) (component 1)"] == 1e5
    assert df_updated.loc[3, f"n_e (Sanders2016 ([OII])) (component 1)"] == 1e5
    assert df_updated.loc[4, f"n_e (Sanders2016 ([OII])) (component 1)"] == 1e5
    assert df_updated.loc[5, f"n_e (Sanders2016 ([OII])) (component 1)"] == 1
    assert df_updated.loc[6, f"n_e (Sanders2016 ([OII])) (component 1)"] == 1
    assert df_updated.loc[7, f"n_e (Sanders2016 ([OII])) (component 1)"] == 1
    assert df_updated.loc[8, f"n_e (Sanders2016 ([OII])) (component 1)"] == n_e_truth

    # Test case 5: test w/o suffix
    df = pd.DataFrame({
        "[OII] ratio": [np.nan, np.nan, 0.1, -0.2, 0.3, 1.6, 2.0, 999, 1.0],
    })
    df_updated = compute_electron_density(df=df, ratio="[OII]", diagnostic="Sanders2016")
    assert np.isnan(df_updated.loc[0, f"n_e (Sanders2016 ([OII]))"])
    assert np.isnan(df_updated.loc[1, f"n_e (Sanders2016 ([OII]))"])
    assert df_updated.loc[2, f"n_e (Sanders2016 ([OII]))"] == 1e5
    assert df_updated.loc[3, f"n_e (Sanders2016 ([OII]))"] == 1e5
    assert df_updated.loc[4, f"n_e (Sanders2016 ([OII]))"] == 1e5
    assert df_updated.loc[5, f"n_e (Sanders2016 ([OII]))"] == 1
    assert df_updated.loc[6, f"n_e (Sanders2016 ([OII]))"] == 1
    assert df_updated.loc[7, f"n_e (Sanders2016 ([OII]))"] == 1
    assert df_updated.loc[8, f"n_e (Sanders2016 ([OII]))"] == n_e_truth

    #//////////////////////////////////////////////////////
    # Test set 3: Sanders [SII]-based measurements 
    # Test case 1: valid input 
    R = 1.0
    n_e_truth = 496.1662269129286
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[SII]", R=np.array([R, R, R]))
    assert np.all(np.isclose(n_e, n_e_truth))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 2: upper/lower limit saturation
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[SII]", R=np.array([0.1, -0.2, 0.38]))
    assert np.all(n_e == 1e5)
    assert not any(lolim_mask)
    assert all(uplim_mask)

    # Lower limit 
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[SII]", R=np.array([1.46, 2.0, 999]))
    assert np.all(n_e == 1)
    assert all(lolim_mask)
    assert not any(uplim_mask)

    # Test case 3: NaNs
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[SII]", R=np.array([np.nan, np.nan, np.nan]))
    assert all(np.isnan(n_e))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 3: infs
    n_e, lolim_mask, uplim_mask = get_n_e_Sanders2016(ratio="[SII]", R=np.array([np.inf, np.inf, np.inf]))
    assert all(np.isnan(n_e))
    assert not any(lolim_mask)
    assert not any(uplim_mask)

    # Test case 4: test inside DataFrame 
    df = pd.DataFrame({
        "[SII] ratio (component 1)": [np.nan, np.nan, 0.1, -0.2, 0.3, 1.6, 2.0, 999, 1.0],
    })
    df_updated = compute_electron_density(df=df, ratio="[SII]", diagnostic="Sanders2016", s=" (component 1)")
    assert np.isnan(df_updated.loc[0, f"n_e (Sanders2016 ([SII])) (component 1)"])
    assert np.isnan(df_updated.loc[1, f"n_e (Sanders2016 ([SII])) (component 1)"])
    assert df_updated.loc[2, f"n_e (Sanders2016 ([SII])) (component 1)"] == 1e5
    assert df_updated.loc[3, f"n_e (Sanders2016 ([SII])) (component 1)"] == 1e5
    assert df_updated.loc[4, f"n_e (Sanders2016 ([SII])) (component 1)"] == 1e5
    assert df_updated.loc[5, f"n_e (Sanders2016 ([SII])) (component 1)"] == 1
    assert df_updated.loc[6, f"n_e (Sanders2016 ([SII])) (component 1)"] == 1
    assert df_updated.loc[7, f"n_e (Sanders2016 ([SII])) (component 1)"] == 1
    assert df_updated.loc[8, f"n_e (Sanders2016 ([SII])) (component 1)"] == n_e_truth

    # Test case 5: test w/o suffix
    df = pd.DataFrame({
        "[SII] ratio": [np.nan, np.nan, 0.1, -0.2, 0.3, 1.6, 2.0, 999, 1.0],
    })
    df_updated = compute_electron_density(df=df, ratio="[SII]", diagnostic="Sanders2016")
    assert np.isnan(df_updated.loc[0, f"n_e (Sanders2016 ([SII]))"])
    assert np.isnan(df_updated.loc[1, f"n_e (Sanders2016 ([SII]))"])
    assert df_updated.loc[2, f"n_e (Sanders2016 ([SII]))"] == 1e5
    assert df_updated.loc[3, f"n_e (Sanders2016 ([SII]))"] == 1e5
    assert df_updated.loc[4, f"n_e (Sanders2016 ([SII]))"] == 1e5
    assert df_updated.loc[5, f"n_e (Sanders2016 ([SII]))"] == 1
    assert df_updated.loc[6, f"n_e (Sanders2016 ([SII]))"] == 1
    assert df_updated.loc[7, f"n_e (Sanders2016 ([SII]))"] == 1
    assert df_updated.loc[8, f"n_e (Sanders2016 ([SII]))"] == n_e_truth


if __name__ == "__main__":

    import matplotlib.pyplot as plt 
    plt.ion()
    plt.close("all")
   
    R_vals = np.linspace(0.2, 1.6, 1000)
    n_e_OII, lolim_mask, uplim_mask = get_n_e_Sanders2016("[OII]", R_vals)
    n_e_SII, lolim_mask, uplim_mask = get_n_e_Sanders2016("[SII]", R_vals)

    fig, ax = plt.subplots()
    ax.plot(n_e_OII, R_vals, color="k", ls="-", label="[O II]")
    ax.plot(n_e_SII, R_vals, color="k", ls="--", label="[S II]")
    ax.set_xlim(1e0, 1e5)
    ax.set_ylim(0.2, 1.6)
    ax.set_xscale("log")
    ax.set_ylabel(r"$R$")
    ax.set_ylabel(r"$n_e$ (cm$^{-3}$)")
    ax.legend()